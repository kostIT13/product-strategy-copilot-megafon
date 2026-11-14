"""Review current evidence impact and reopen only an explicitly selected snapshot."""

from datetime import datetime, timezone
import json
from product_strategy_agent.application.ports.workflow_reopen_store import (
    WorkflowReopenStore,
)
from product_strategy_agent.application.services.claim_lifecycle_service import (
    impact_from_snapshot,
)
from product_strategy_agent.domain.projects.workflow_reopen import (
    WorkflowReopen,
    plan_reopen,
    review_hash,
)
from product_strategy_agent.domain.projects.workspace import validate_workspace_id


class WorkflowReopenService:
    def __init__(self, store: WorkflowReopenStore):
        self.store = store

    def review(self, project_id):
        validate_workspace_id(project_id)
        with self.store.access(project_id):
            snapshot = self.store.capture_claims(project_id)
            impact = impact_from_snapshot(project_id, snapshot)
            state = json.loads(snapshot["state"])
            return {
                "format_version": "psa-workflow-review-v1",
                "project_id": project_id,
                "workflow_version": impact["workflow_version"],
                "status": state["status"],
                "stages": state["stages"],
                "historical_approvals": state.get("approvals", []),
                "reopen_history": state.get("reopen_history", []),
                "rollback_history": state.get("rollback_history", []),
                "claim_impact": impact,
                "review_hash": review_hash(
                    snapshot["state"], snapshot["events"], snapshot["inputs"]
                ),
                "semantic_alignment_verified": False,
                "human_decision_changed": False,
                "reopen_authorized": False,
                "rollback_authorized": False,
            }

    def reopen(self, project_id, command):
        validate_workspace_id(project_id)
        command = WorkflowReopen.model_validate(command)
        with self.store.access(project_id):
            replay = self.store.replay(project_id, command)
            if replay is not None:
                return replay
            snapshot = self.store.capture_claims(project_id)
            impact_from_snapshot(project_id, snapshot)
            now = (
                datetime.now(timezone.utc)
                .isoformat(timespec="seconds")
                .replace("+00:00", "Z")
            )
            after, event = plan_reopen(
                command, snapshot["state"], snapshot["events"], snapshot["inputs"], now
            )
            return self.store.commit(
                project_id,
                command,
                snapshot["state"],
                after,
                snapshot["events"],
                event,
                snapshot["inputs"],
            )
