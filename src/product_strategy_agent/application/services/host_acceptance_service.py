"""Capture evidence for later review, never promote claims into native support."""

from datetime import datetime, timezone
from uuid import UUID
from product_strategy_agent.application.ports.host_acceptance_store import (
    HostAcceptanceStore,
)
from product_strategy_agent.domain.automation.contracts import fingerprint
from product_strategy_agent.domain.automation.host_profiles import PlanHost
from product_strategy_agent.domain.automation.host_acceptance import (
    REQUIRED,
    AcceptanceTask,
    RecordHostAcceptance,
    AcceptanceRecord,
    receipt,
)


class HostAcceptanceService:
    def __init__(self, profiles, store: HostAcceptanceStore):
        self.profiles, self.store = profiles, store

    def _task(self, plan, operation_id):
        if plan.mode != "native":
            raise ValueError("host acceptance requires explicit native plan scope")
        if not isinstance(operation_id, UUID):
            raise ValueError("host acceptance requires operation UUID")
        packet = self.profiles.plan(plan)
        return AcceptanceTask(
            operation_id=operation_id,
            plan=plan,
            catalog_sha256=packet["catalog_sha256"],
            catalog_version=packet["catalog_version"],
            instruction_hashes={
                item["path"]: item["sha256"] for item in packet["instruction_surfaces"]
            },
            required_capabilities=sorted(REQUIRED[plan.feature]),
        )

    def prepare(self, plan, operation_id):
        plan = PlanHost.model_validate(plan)
        task = self._task(plan, operation_id)
        return {
            "task": task.model_dump(mode="json"),
            "task_fingerprint": fingerprint(task),
            "execution_started": False,
            "native_activation_allowed": False,
            "external_transfer_authorized": False,
            "human_approval_granted": False,
        }

    def _freshness(self, task):
        try:
            return (
                "current"
                if self._task(task.plan, task.operation_id) == task
                else "stale"
            )
        except (ValueError, OSError):
            return "unavailable"

    def _packet(self, record, historical):
        return {
            "receipt": receipt(record),
            "historical": historical,
            "freshness": self._freshness(record.command.task),
        }

    def record(self, command, reader):
        command = RecordHostAcceptance.model_validate(command)
        with self.store.access():
            old = self.store.read(command.task.operation_id)
            if old is not None:
                if old.command != command:
                    raise ValueError(
                        "host acceptance UUID belongs to a different report"
                    )
                return self._packet(old, True)
            if self._freshness(command.task) != "current":
                raise ValueError(
                    "host acceptance scope/instructions stale or unavailable; prepare a new UUID"
                )
            captured = reader.capture(command.evidence)
            if self._freshness(command.task) != "current":
                raise ValueError("host instructions changed during evidence capture")
            record = AcceptanceRecord(
                command=command,
                captured=captured,
                recorded_at=datetime.now(timezone.utc),
            )
            return self._packet(self.store.publish(record), False)

    def show(self, operation_id):
        with self.store.access():
            record = self.store.read(operation_id)
            if record is None:
                raise ValueError("host acceptance report not found")
            return self._packet(record, True)

    def pending(self):
        with self.store.access():
            return self.store.pending()

    def recover(self, operation_id):
        with self.store.access():
            return self._packet(self.store.recover(operation_id), True)
