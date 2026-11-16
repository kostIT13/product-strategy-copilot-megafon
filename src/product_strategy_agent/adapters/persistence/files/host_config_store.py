"""Private write-ahead config intent, active guard and exact forward recovery."""

from datetime import datetime, timezone
import os
from pathlib import Path
from uuid import UUID
from product_strategy_agent.adapters.persistence.files.host_config_audit import audit
from product_strategy_agent.adapters.persistence.files.host_config_publication import (
    preserve,
    publish,
    staged,
)
from product_strategy_agent.adapters.persistence.files.paths import confined
from product_strategy_agent.adapters.persistence.files.project_lock import project_lock
from product_strategy_agent.adapters.persistence.files.source_search_repository import (
    read_bounded,
)
from product_strategy_agent.adapters.persistence.files.workspace_repository import (
    durable_write,
    sync_directory,
)
from product_strategy_agent.domain.automation.contracts import fingerprint
from product_strategy_agent.domain.automation.handoffs import strict_json
from product_strategy_agent.domain.automation.host_config import digest, parse_config
from product_strategy_agent.domain.automation.host_config_record import decode, encode

PREFIX = ".psa/host-config/v1"


class FileHostConfigStore:
    def __init__(self, root):
        self.root = Path(root).resolve()

    def access(self):
        return project_lock(self.root, "psa-host-config")

    def audit(self):
        return audit(self)

    def _path(self, name):
        return confined(self.root, f"{PREFIX}/{name}")

    def folder(self, identifier):
        if not isinstance(identifier, UUID):
            raise ValueError("host config requires UUID")
        return self._path(identifier.hex)

    def read_config(self):
        path = confined(self.root, ".codex/config.toml")
        if not path.exists():
            return None
        if not path.is_file():
            raise ValueError("config target must be a regular local file")
        try:
            text = read_bounded(path, 64000).decode("utf-8")
        except UnicodeError:
            raise ValueError("config target must be UTF-8 TOML") from None
        parse_config(text)
        return text

    def load(self, identifier):
        folder = self.folder(identifier)
        if not folder.exists():
            return None
        record = decode(
            read_bounded(confined(folder, "operation.json"), 512000), identifier
        )
        if record.command.action == "restore":
            source_id = record.command.source_operation_id
            if source_id == identifier:
                raise ValueError("config restore cannot reference itself")
            source = decode(
                read_bounded(
                    confined(self.folder(source_id), "operation.json"), 512000
                ),
                source_id,
            )
            if (
                source.command.action == "restore"
                or source.command.plan != record.command.plan
                or record.before != source.after
                or record.after != source.before
                or not self.completion(source)
            ):
                raise ValueError("config restore source/preimage mismatch")
        return record

    def completion(self, record):
        path = confined(self.folder(record.command.operation_id), "COMMITTED.json")
        if not path.exists():
            return None
        body = strict_json(read_bounded(path, 4096))
        self._validate_receipt(record, body)
        return body

    def _validate_receipt(self, record, body):
        if (
            not isinstance(body, dict)
            or set(body) != {"record_hash", "applied_at"}
            or body["record_hash"] != fingerprint(record)
            or not isinstance(body["applied_at"], str)
        ):
            raise ValueError("config completion receipt invalid")
        try:
            if datetime.fromisoformat(body["applied_at"]).tzinfo is None:
                raise ValueError("missing timezone")
        except ValueError:
            raise ValueError("config completion timestamp invalid") from None

    def _stage(self, record, name):
        return confined(
            self.folder(record.command.operation_id), name + ".pending.json"
        )

    def _marker(self, record, binding):
        def validate(body):
            if body != binding:
                raise ValueError("config staged guard mismatch")

        return publish(
            self._path("ACTIVE.json"),
            self._stage(record, "ACTIVE"),
            self.folder(record.command.operation_id),
            binding,
            validate,
            durable_write,
        )

    def _receipt(self, record, body):
        return publish(
            confined(self.folder(record.command.operation_id), "COMMITTED.json"),
            self._stage(record, "COMMITTED"),
            self.folder(record.command.operation_id),
            body,
            lambda value: self._validate_receipt(record, value),
            durable_write,
        )

    def _active(self):
        path = self._path("ACTIVE.json")
        if not path.exists():
            return None
        body = strict_json(read_bounded(path, 4096))
        try:
            if (
                not isinstance(body, dict)
                or set(body) != {"operation_id", "record_hash"}
                or str(UUID(body["operation_id"])) != body["operation_id"]
                or not isinstance(body["record_hash"], str)
                or len(body["record_hash"]) != 64
                or set(body["record_hash"]) - set("0123456789abcdef")
            ):
                raise ValueError("invalid marker")
        except (ValueError, TypeError, KeyError, AttributeError):
            raise ValueError(
                "config active guard invalid; preserve for inspection"
            ) from None
        return body

    def pending(self):
        root = self._path("")
        if not root.exists():
            return {"operations": []}
        entries = [path for path in root.iterdir() if path.name != "ACTIVE.json"]
        if len(entries) > 1000:
            raise ValueError("config history exceeds 1000 operations")
        rows = []
        for path in sorted(entries):
            try:
                identifier = UUID(hex=path.name)
                if path.name != identifier.hex or not path.is_dir():
                    raise ValueError("invalid folder")
            except ValueError:
                raise ValueError(
                    "unrecognized config journal entry; preserve for inspection"
                ) from None
            try:
                record = self.load(identifier)
                if self.completion(record):
                    continue
                status = "prepared"
            except (ValueError, OSError):
                status = "corrupt_or_incomplete"
            rows.append({"operation_id": str(identifier), "status": status})
        return {
            "operations": rows,
            "active": self._active(),
        }

    def ready(self):
        packet = self.pending()
        if packet.get("active") is not None or packet["operations"]:
            raise ValueError(
                "config operation pending; inspect and explicitly recover before new changes"
            )

    def begin(self, record):
        folder = self.folder(record.command.operation_id)
        folder.parent.mkdir(parents=True, exist_ok=True)
        if len([p for p in folder.parent.iterdir() if p.name != "ACTIVE.json"]) >= 1000:
            raise ValueError("config history reached 1000 operations; history retained")
        folder.mkdir()
        durable_write(confined(folder, "operation.json"), encode(record))
        sync_directory(folder)
        sync_directory(folder.parent)

    def _replace_config(self, record):
        target = confined(self.root, ".codex/config.toml")
        target.parent.mkdir(parents=True, exist_ok=True)
        if record.after is None:
            if target.exists():
                target.unlink()
        else:
            temporary = confined(
                self.root, f".codex/.psa-config-{record.command.operation_id.hex}.tmp"
            )
            if temporary.exists():
                if read_bounded(temporary, 64000) != record.after.encode("utf-8"):
                    preserve(
                        temporary,
                        self.folder(record.command.operation_id),
                        64000,
                        durable_write,
                    )
            if not temporary.exists():
                durable_write(temporary, record.after.encode("utf-8"))
            os.replace(temporary, target)
        sync_directory(target.parent)

    def commit(self, record):
        marker = self._path("ACTIVE.json")
        binding = {
            "operation_id": str(record.command.operation_id),
            "record_hash": fingerprint(record),
        }
        old = self.completion(record)
        if marker.exists() and self._active() != binding:
            raise ValueError("another config operation is active")
        if old is None:
            captured = staged(
                self._stage(record, "COMMITTED"),
                lambda value: self._validate_receipt(record, value),
            )
            if captured is not None:
                old = self._receipt(record, captured)
        if old is None:
            current = digest(self.read_config())
            if current not in {digest(record.before), digest(record.after)}:
                raise ValueError(
                    "config changed outside this operation; refusing recovery overwrite"
                )
            if not marker.exists():
                self._marker(record, binding)
            if current != digest(record.after):
                self._replace_config(record)
            # Detect persistent unrelated writes before publishing completion.
            if digest(self.read_config()) != digest(record.after):
                raise ValueError(
                    "config changed before completion; preserve active operation"
                )
            old = {
                "record_hash": fingerprint(record),
                "applied_at": datetime.now(timezone.utc).isoformat(),
            }
            old = self._receipt(record, old)
        if marker.exists():
            marker.unlink()
            sync_directory(marker.parent)
        return old
