"""Validate direct IDE input; persistence owns version/reservation/commit checks."""
from uuid import UUID
from product_strategy_agent.application.ports.research_artifact_store import ResearchArtifactStore
from product_strategy_agent.domain.projects.research_artifact import RecordResearchArtifact
from product_strategy_agent.domain.projects.workspace import validate_workspace_id


class ResearchArtifactService:
    def __init__(self, store: ResearchArtifactStore):
        self.store = store

    def status(self, project_id):
        return self.store.status(validate_workspace_id(project_id))

    def record(self, project_id, command):
        return self.store.record(validate_workspace_id(project_id), RecordResearchArtifact.model_validate(command))

    def show(self, project_id, operation_id=None):
        return self.store.show(validate_workspace_id(project_id), UUID(str(operation_id)) if operation_id else None)

    def pending(self, project_id):
        project_id = validate_workspace_id(project_id)
        return {"project_id": project_id, "preparations": self.store.pending(project_id), "read_only": True}

    def recover(self, project_id, operation_id):
        return self.store.recover(validate_workspace_id(project_id), UUID(str(operation_id)))
