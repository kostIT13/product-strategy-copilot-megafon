"""Immutable local host-observation records; caller holds one shared OS lock."""

import os
from pathlib import Path
from uuid import UUID
from product_strategy_agent.adapters.persistence.files.paths import confined
from product_strategy_agent.adapters.persistence.files.project_lock import project_lock
from product_strategy_agent.adapters.persistence.files.source_search_repository import (
    read_bounded,
)
from product_strategy_agent.adapters.persistence.files.workspace_repository import (
    durable_write,
    sync_directory,
)
from product_strategy_agent.domain.automation.host_acceptance import encode, decode


class FileHostAcceptanceStore:
    def __init__(self, root):
        self.root = Path(root).resolve()

    def access(self):
        return project_lock(self.root, "psa-host-acceptance")

    def _path(self, operation_id, pending=False):
        if not isinstance(operation_id, UUID):
            raise ValueError("host acceptance requires operation UUID")
        return confined(
            self.root,
            f".psa/host-acceptance/v1/{operation_id.hex}{'.pending' if pending else ''}.json",
        )

    def read(self, operation_id):
        final = self._path(operation_id)
        if final.exists():
            return decode(read_bounded(final, 256000), operation_id)
        if self._path(operation_id, True).exists():
            raise ValueError(
                "host acceptance publication pending; inspect and explicitly recover"
            )
        return None

    def _install(self, pending, final):
        if final.exists():
            raise ValueError("host acceptance record already exists")
        os.replace(pending, final)
        sync_directory(final.parent)

    def publish(self, record):
        identifier = record.command.task.operation_id
        if self.read(identifier) is not None:
            raise ValueError("host acceptance operation already exists")
        path = self._path(identifier, True)
        path.parent.mkdir(parents=True, exist_ok=True)
        if len(list(path.parent.iterdir())) >= 1000:
            raise ValueError("host acceptance reached 1000 records; history retained")
        durable_write(path, encode(record))
        sync_directory(path.parent)
        decode(read_bounded(path, 256000), identifier)
        self._install(path, self._path(identifier))
        return self.read(identifier)

    def pending(self):
        folder = self._path(UUID(int=0)).parent
        if not folder.exists():
            return {"records": []}
        entries = list(folder.iterdir())
        if len(entries) > 1000:
            raise ValueError("host acceptance exceeds supported history limit")
        rows = []
        for path in sorted(entries):
            suffix = ".pending.json" if path.name.endswith(".pending.json") else ".json"
            try:
                identifier = UUID(hex=path.name.removesuffix(suffix))
                if path.name != identifier.hex + suffix:
                    raise ValueError("invalid record name")
            except ValueError:
                raise ValueError(
                    "unrecognized host acceptance record; preserve for inspection"
                ) from None
            if suffix == ".pending.json":
                try:
                    record = decode(read_bounded(path, 256000), identifier)
                    status = "prepared"
                except (ValueError, OSError):
                    status = "corrupt_or_incomplete"
                rows.append({"operation_id": str(identifier), "status": status})
        return {"records": rows}

    def recover(self, operation_id):
        final = self._path(operation_id)
        if final.exists():
            return self.read(operation_id)
        pending = self._path(operation_id, True)
        if not pending.exists():
            raise ValueError("no captured host acceptance publication")
        decode(read_bounded(pending, 256000), operation_id)
        self._install(pending, final)
        return self.read(operation_id)
