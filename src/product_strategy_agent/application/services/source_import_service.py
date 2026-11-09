"""Import a captured source once, preserving exact replay before file/network reads."""
from datetime import datetime, timezone
import json
from product_strategy_agent.application.ports.source_import_store import SourceImportStore, SourceReader
from product_strategy_agent.domain.projects.source_import import SourceImport
from product_strategy_agent.domain.projects.workspace import validate_workspace_id


class SourceImportService:
    def __init__(self, store: SourceImportStore, reader: SourceReader):
        self.store, self.reader = store, reader

    def run(self, project_id, command):
        project_id = validate_workspace_id(project_id)
        command = SourceImport.model_validate(command)
        with self.store.access(project_id):
            replay = self.store.replay(project_id, command)
            if replay is not None:
                return replay
            snapshot = self.store.capture(project_id)
            state = json.loads(snapshot["state"])
            version = state.get("workflow_version", 0)
            if state.get("schema_version") != 1 or state.get("project_id") != project_id or type(version) is not int or version < 0:
                raise ValueError("invalid source-import workflow state")
            if command.expected_workflow_version is not None and command.expected_workflow_version != version:
                raise ValueError("expected_workflow_version conflict; inspect current state before source read/fetch")
            material, text = self.reader.read(command)
            snapshot = self.store.capture_source(project_id, snapshot, material, text)
            now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
            return self.store.commit_source(project_id, command, snapshot, material, text, now)
