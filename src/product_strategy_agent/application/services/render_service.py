"""Render or adopt a captured case without changing author documents or approvals."""
from datetime import datetime, timezone
import json
from product_strategy_agent.application.ports.render_store import RenderStore
from product_strategy_agent.domain.projects.render_plan import RenderRequest
from product_strategy_agent.domain.projects.workspace import validate_workspace_id


class RenderService:
    def __init__(self, store: RenderStore):
        self.store = store

    def run(self, project_id, command):
        project_id = validate_workspace_id(project_id)
        command = RenderRequest.model_validate(command)
        with self.store.access(project_id):
            replay = self.store.replay(project_id, command)
            if replay is not None:
                return replay
            snapshot = self.store.capture_render(project_id)
            state = json.loads(snapshot["state"])
            version = state.get("workflow_version", 0)
            if state.get("schema_version") != 1 or state.get("project_id") != project_id or type(version) is not int or version < 0:
                raise ValueError("invalid render workflow state")
            if command.expected_workflow_version is not None and command.expected_workflow_version != version:
                raise ValueError("expected_workflow_version conflict; review current render inputs")
            if command.mode == "render":
                if command.builder_version not in {None, 2}:
                    raise ValueError("new renders require builder v2; v1 is reserved for historical replay")
                command = command.model_copy(update={"builder_version": 2})
            now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
            return self.store.commit_render(project_id, command, snapshot, now)
