"""Explicit disabled-only config changes with conditional restore; never enable or launch."""

from datetime import datetime, timezone
import hashlib
import json
from product_strategy_agent.domain.automation.host_config import (
    PlanConfigChange,
    ApplyConfigChange,
    digest,
    merge,
    assert_inactive,
)
from product_strategy_agent.domain.automation.host_config_record import ConfigRecord


def scope_hash(packet):
    body = {
        key: packet[key]
        for key in (
            "request",
            "catalog_sha256",
            "instruction_surfaces",
            "review",
            "preview",
        )
    }
    return hashlib.sha256(
        json.dumps(body, ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()


class HostConfigService:
    def __init__(self, previews, profiles, store):
        self.previews, self.profiles, self.store = previews, profiles, store

    def _proposal(self, command):
        before = self.store.read_config()
        if command.action == "restore":
            source = self.store.load(command.source_operation_id)
            if (
                source is None
                or source.command.action == "restore"
                or not self.store.completion(source)
                or source.command.plan != command.plan
            ):
                raise ValueError(
                    "restore requires a completed original config operation with matching scope"
                )
            if digest(before) != digest(source.after):
                raise ValueError(
                    "config changed after source operation; cannot restore over later edits"
                )
            after = source.before
            assert_inactive(after)
            profile = self.profiles.plan(command.plan)
            binding = hashlib.sha256(
                json.dumps(profile, ensure_ascii=False, sort_keys=True).encode()
            ).hexdigest()
            fragment = None
        else:
            preview = self.previews.preview(
                command.plan, command.interpreter, command.review_operation_id
            )
            fragment = preview["preview"]["content"]
            after = merge(before, fragment, command.action)
            binding = scope_hash(preview)
            if command.action == "disable":
                fragment = (
                    None  # Do not expose existing managed values in the plan response.
                )
        return before, after, binding, fragment

    def plan(self, command):
        command = PlanConfigChange.model_validate(command)
        with self.store.access():
            self.store.ready()
            if self.store.load(command.operation_id) is not None:
                raise ValueError("config plan requires a new operation UUID")
            before, after, binding, fragment = self._proposal(command)
            prepared = ApplyConfigChange(
                **command.model_dump(),
                expected_before_hash=digest(before),
                expected_after_hash=digest(after),
                scope_hash=binding,
            )
            return {
                "command": prepared.model_dump(mode="json"),
                "target_hint": ".codex/config.toml",
                "managed_fragment": fragment,
                "configuration_written": False,
                "native_activation_allowed": False,
                "existing_content_returned": False,
                "backup_required": True,
            }

    def _packet(self, record, completion, historical):
        try:
            matches = digest(self.store.read_config()) == digest(record.after)
        except (ValueError, OSError):
            matches = None
        return {
            "receipt": {
                "operation_id": str(record.command.operation_id),
                "action": record.command.action,
                "changed_by": record.command.changed_by,
                "reason": record.command.reason,
                **completion,
                "before_hash": digest(record.before),
                "after_hash": digest(record.after),
                "native_activation_allowed": False,
                "host_acceptance_verified": False,
            },
            "historical": historical,
            "current_matches_after": matches,
            "execution_started": False,
            "existing_content_returned": False,
        }

    def apply(self, command):
        command = ApplyConfigChange.model_validate(command)
        with self.store.access():
            old = self.store.load(command.operation_id)
            if old is not None:
                if old.command != command:
                    raise ValueError("config UUID belongs to a different command")
                completion = self.store.completion(old)
                if completion is None:
                    raise ValueError(
                        "config publication pending; explicitly recover, do not retry apply"
                    )
                return self._packet(old, completion, True)
            self.store.ready()
            before, after, binding, _fragment = self._proposal(command)
            if (digest(before), digest(after), binding) != (
                command.expected_before_hash,
                command.expected_after_hash,
                command.scope_hash,
            ):
                raise ValueError(
                    "prepared config/scope hashes are stale; prepare a new operation"
                )
            record = ConfigRecord(
                schema_version=1,
                command=command,
                before=before,
                after=after,
                prepared_at=datetime.now(timezone.utc),
            )
            self.store.begin(record)
            return self._packet(record, self.store.commit(record), False)

    def show(self, identifier):
        with self.store.access():
            record = self.store.load(identifier)
            if record is None or not self.store.completion(record):
                raise ValueError(
                    "config operation incomplete or absent; inspect pending"
                )
            return self._packet(record, self.store.completion(record), True)

    def pending(self):
        with self.store.access():
            return self.store.pending()

    def audit(self):
        with self.store.access():
            return self.store.audit()

    def recover(self, identifier):
        with self.store.access():
            record = self.store.load(identifier)
            if record is None:
                raise ValueError("config intent not found")
            return self._packet(record, self.store.commit(record), True)
