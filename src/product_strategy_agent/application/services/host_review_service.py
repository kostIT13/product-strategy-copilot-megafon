"""Record explicit report assessment; never promote native capability or overwrite reports."""

from datetime import datetime, timezone
from product_strategy_agent.domain.automation.contracts import fingerprint
from product_strategy_agent.domain.automation.host_reviews import (
    CHECKS,
    ReviewHostReport,
    HostReviewRecord,
    validate_parent,
    receipt,
)
from product_strategy_agent.domain.automation.host_acceptance import (
    receipt as report_receipt,
)


class HostReviewService:
    def __init__(self, observations, store):
        self.observations, self.store = observations, store

    def _report(self, operation_id):
        report = self.observations.store.read(operation_id)
        if report is None:
            raise ValueError("host observation report not found")
        return report

    def prepare(self, report_id, include_evidence=False):
        with self.store.access():
            report = self._report(report_id)
            packet = {
                "report": report_receipt(report),
                "expected_report_hash": fingerprint(report),
                "required_checks": sorted(CHECKS),
                "freshness": self.observations.scope_freshness(report.command.task),
                "native_activation_allowed": False,
                "host_acceptance_verified": False,
            }
            if include_evidence:
                packet["captured_evidence"] = [
                    item.model_dump(mode="json") for item in report.captured
                ]
            return packet

    def _packet(self, record, historical):
        report = self._report(record.command.report_operation_id)
        validate_parent(record, report)
        return {
            "receipt": receipt(record),
            "historical": historical,
            "scope": report.command.task.plan.model_dump(mode="json"),
            "freshness": self.observations.scope_freshness(report.command.task),
        }

    def record(self, command):
        command = ReviewHostReport.model_validate(command)
        with self.store.access():
            old = self.store.read(command.operation_id)
            if old is not None:
                if old.command != command:
                    raise ValueError(
                        "host review UUID belongs to a different assessment"
                    )
                return self._packet(old, True)
            report = self._report(command.report_operation_id)
            record = HostReviewRecord(
                command=command, recorded_at=datetime.now(timezone.utc)
            )
            validate_parent(record, report)
            if (
                command.verdict == "accepted_for_preview"
                and self.observations.scope_freshness(report.command.task) != "current"
            ):
                raise ValueError(
                    "stale host report cannot be adopted for a new preview"
                )
            return self._packet(self.store.publish(record), False)

    def show(self, operation_id):
        with self.store.access():
            record = self.store.read(operation_id)
            if record is None:
                raise ValueError("host review not found")
            return self._packet(record, True)

    def pending(self):
        with self.store.access():
            return self.store.pending()

    def recover(self, operation_id):
        with self.store.access():
            return self._packet(self.store.recover(operation_id), True)

    def select_for_preview(self, operation_id, plan):
        with self.store.access():
            record = self.store.read(operation_id)
            if record is None:
                raise ValueError("host review not found")
            packet = self._packet(record, True)
            if (
                record.command.verdict != "accepted_for_preview"
                or packet["freshness"] != "current"
                or packet["scope"] != plan.model_dump(mode="json")
            ):
                raise ValueError(
                    "selected review does not adopt this current host/version/OS/feature scope"
                )
            return packet["receipt"]
