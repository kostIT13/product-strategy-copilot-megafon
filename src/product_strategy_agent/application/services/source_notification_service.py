"""Explicit source-revision notice; never review, gate approval or import rollback."""

from uuid import UUID
from product_strategy_agent.application.ports.source_notification_reader import (
    SourceNotificationReader,
)
from product_strategy_agent.application.services.hook_preflight_service import (
    nonrecursive,
)
from product_strategy_agent.domain.automation.contracts import fingerprint
from product_strategy_agent.domain.automation.hooks import HookRequest, HookResult
from product_strategy_agent.domain.automation.source_notification import RevisionSummary
from product_strategy_agent.domain.projects.workspace import validate_workspace_id


class SourceNotificationService:
    def __init__(self, reader: SourceNotificationReader):
        self.reader = reader

    def prepare(self, project_id, operation_id):
        validate_workspace_id(project_id)
        if not isinstance(operation_id, UUID):
            raise ValueError("source notification requires operation UUID")
        with nonrecursive(), self.reader.access(project_id):
            return HookRequest(
                operation_id=operation_id,
                trigger="source_revision",
                target=self.reader.target(project_id),
            ).model_dump(mode="json")

    def check(self, command):
        command = HookRequest.model_validate(command)
        if command.trigger != "source_revision":
            raise ValueError("source notification requires source_revision trigger")
        project_id = command.target.project_id
        validate_workspace_id(project_id)

        def result(status, issues):
            return HookResult(
                operation_id=command.operation_id,
                request_fingerprint=fingerprint(command),
                status=status,
                issues=issues,
            ).model_dump(mode="json")

        with nonrecursive(), self.reader.access(project_id):
            if self.reader.target(project_id) != command.target:
                return result(
                    "blocked", ["notification snapshot is stale; prepare a new UUID"]
                )
            try:
                summary = RevisionSummary.model_validate(
                    self.reader.summary(project_id)
                )
            except (ValueError, OSError, KeyError, TypeError):
                return result(
                    "failed",
                    ["source revision summary unavailable; inspect psa revisit list"],
                )
            if self.reader.target(project_id) != command.target:
                return result(
                    "blocked", ["case changed during notification; prepare a new UUID"]
                )
            if not summary.revision_count:
                return result(
                    "skipped",
                    ["no source revision events; initial import is not a revision"],
                )
            if summary.pending_count:
                return result(
                    "blocked",
                    [
                        f"Human revisit required: {summary.pending_count} pending source revision(s), "
                        f"{summary.affected_claim_count} affected claim(s), {summary.affected_decision_count} affected decision(s). "
                        "Inspect psa revisit list; notification does not record human review.",
                    ],
                )
            return result("passed", [])
