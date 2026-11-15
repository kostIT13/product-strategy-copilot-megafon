"""Project existing revisit data; source import and human review remain unchanged."""

from product_strategy_agent.adapters.persistence.files.hook_preflight_reader import (
    FileHookPreflightReader,
)
from product_strategy_agent.domain.automation.source_notification import RevisionSummary
from product_strategy_agent.revisit import build_revisit_report


class FileSourceNotificationReader:
    def __init__(self, root):
        self.snapshots = FileHookPreflightReader(root)

    def access(self, project_id):
        return self.snapshots.access(project_id)

    def target(self, project_id):
        return self.snapshots.target(project_id)

    def summary(self, project_id):
        with self.access(project_id) as case:
            report = build_revisit_report(case)
            pending = [
                item
                for item in report["revisions"]
                if item["status"] == "pending_review"
            ]
            return RevisionSummary(
                revision_count=len(report["revisions"]),
                pending_count=len(pending),
                affected_claim_count=len(
                    {
                        identifier
                        for item in pending
                        for identifier in item["affected_claim_ids"]
                    }
                ),
                affected_decision_count=len(
                    {
                        identifier
                        for item in pending
                        for identifier in item["affected_decision_ids"]
                    }
                ),
            )
