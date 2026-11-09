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

    def review_for_approval(self, project_id, operation_id, version):
        """Resolve the exact current draft; caller must hold the project write lock."""
        status = self.status(project_id)
        if status["version"] == 0:
            if operation_id is not None or version is not None:
                raise ValueError("no committed structured research plan to approve")
            return None
        if operation_id is None or type(version) is not int or version < 1:
            raise ValueError("structured plan approval requires artifact_operation and artifact_version")
        operation_id = UUID(str(operation_id))
        if status["version"] != version or status["head"]["operation_id"] != str(operation_id):
            raise ValueError("approve the current structured plan operation and version after human review")
        item = self.show(project_id, operation_id)
        if item["base_inputs_changed"]:
            raise ValueError("structured plan inputs changed; record and review a fresh draft before approval")
        return {"kind": "research_plan", "operation_id": str(operation_id), "version": version,
                "manifest_hash": status["head"]["manifest_hash"],
                "base_case_hash": item["receipt"]["base_case_hash"]}
