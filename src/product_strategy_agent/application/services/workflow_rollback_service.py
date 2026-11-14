"""Publish only a reviewed, explicitly requested backward workflow transition."""

from datetime import datetime, timezone
from product_strategy_agent.application.ports.workflow_reopen_store import (
    WorkflowReopenStore,
)
from product_strategy_agent.application.services.claim_lifecycle_service import (
    impact_from_snapshot,
)
from product_strategy_agent.domain.projects.workflow_rollback import (
    WorkflowRollback,
    plan_rollback,
)
from product_strategy_agent.domain.projects.workspace import validate_workspace_id


class WorkflowRollbackService:
    def __init__(self, store: WorkflowReopenStore):
        self.store = store

    def rollback(self, project_id, command):
        validate_workspace_id(project_id)
        command = WorkflowRollback.model_validate(command)
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
            after, event = plan_rollback(
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
