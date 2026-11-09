"""Explicit forward recovery never creates a new human approval."""
from uuid import UUID
from product_strategy_agent.application.ports.file_workflow_store import WorkflowStore
from product_strategy_agent.domain.projects.workspace import validate_workspace_id


class WorkflowRecoveryService:
    def __init__(self, store: WorkflowStore):
        self.store = store

    def pending(self, project_id):
        return self.store.pending(validate_workspace_id(project_id))

    def recover(self, project_id, operation_id):
        return self.store.recover(validate_workspace_id(project_id), UUID(str(operation_id)))
