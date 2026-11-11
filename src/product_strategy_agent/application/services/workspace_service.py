"""Initialize file cases and explicitly recover interrupted preparation without model calls."""
from datetime import datetime, timezone
from uuid import UUID, uuid4
from product_strategy_agent.application.ports.workspace_store import WorkspaceStore
from product_strategy_agent.domain.projects.workspace import validate_workspace_id, current_workspace_seed


class WorkspaceService:
    def __init__(self, store: WorkspaceStore):
        self.store = store

    def initialize(self, project_id):
        validate_workspace_id(project_id)
        now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        return self.store.create(current_workspace_seed(project_id, now), uuid4())

    def pending(self, project_id):
        return self.store.pending(validate_workspace_id(project_id))

    def recover(self, project_id, operation_id):
        return self.store.recover(validate_workspace_id(project_id), UUID(str(operation_id)))
