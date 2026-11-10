"""Import a captured source once, preserving exact replay before file/network reads."""
from datetime import datetime, timezone
import json
from product_strategy_agent.application.ports.source_import_store import SourceImportStore, SourceReader
from product_strategy_agent.domain.projects.source_import import SourceImport
from product_strategy_agent.domain.projects.workspace import validate_workspace_id
from product_strategy_agent.domain.projects.source_lifecycle import source_statuses
from product_strategy_agent.domain.projects.source_import import source_id


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
            sources = [json.loads(line) for line in snapshot["sources"].splitlines() if line.strip()]
            events = [json.loads(line) for line in snapshot["events"].splitlines() if line.strip()]
            statuses = source_statuses(sources, events)
            if statuses.get(source_id(command.locator)) == "withdrawn" or any(
                statuses[row["source_id"]] == "withdrawn" and row.get("provenance", {}).get("requested_url") == command.locator for row in sources
            ):
                raise ValueError("source is withdrawn; reimport/revision cannot reactivate it")
            material, text = self.reader.read(command)
            if statuses.get(source_id(material["uri"])) == "withdrawn":
                raise ValueError("captured source is withdrawn; publication refused")
            snapshot = self.store.capture_source(project_id, snapshot, material, text)
            now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
            return self.store.commit_source(project_id, command, snapshot, material, text, now)
