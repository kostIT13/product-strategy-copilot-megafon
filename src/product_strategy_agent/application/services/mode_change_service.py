"""Change research depth without advancing stages or granting new approvals."""
from datetime import datetime, timezone
import json
from product_strategy_agent.application.ports.mode_workflow_store import ModeWorkflowStore
from product_strategy_agent.domain.projects.mode_change import ModeChange
from product_strategy_agent.domain.projects.research_modes import MODE_PROFILES
from product_strategy_agent.domain.projects.workspace import validate_workspace_id


class ModeChangeService:
    def __init__(self, store: ModeWorkflowStore):
        self.store = store

    def change(self, project_id, command):
        project_id = validate_workspace_id(project_id)
        command = ModeChange.model_validate(command)
        with self.store.access(project_id):
            replay = self.store.replay(project_id, command)
            if replay is not None:
                return replay
            snapshot = self.store.capture(project_id)
            state = json.loads(snapshot["state"])
            if state.get("schema_version") != 1 or state.get("project_id") != project_id:
                raise ValueError("unsupported or mismatched case state")
            version = state.get("workflow_version", 0)
            if type(version) is not int or version < 0:
                raise ValueError("invalid workflow version")
            if command.expected_workflow_version is not None and command.expected_workflow_version != version:
                raise ValueError("expected_workflow_version conflict; review current workflow state")
            if state.get("status") == "completed":
                raise ValueError("Cannot change the mode of a completed project")
            previous = state.get("mode", "decision_grade")
            if previous not in MODE_PROFILES:
                raise ValueError("unsupported current research mode")
            if previous == command.mode:
                raise ValueError(f"Project already uses mode '{command.mode}'")
            if state.get("stages", {}).get("source_collection") == "done":
                sources, gaps = ([json.loads(line) for line in snapshot[name].splitlines() if line.strip()] for name in ("sources", "gaps"))
                profile = MODE_PROFILES[command.mode]
                shortage = profile["source_shortage_exception"] and sources and any(g.get("status") == "open" and g.get("priority") == "high" for g in gaps)
                if len(sources) < profile["minimum_sources"] and not shortage:
                    raise ValueError(f"Mode '{command.mode}' requires at least {profile['minimum_sources']} sources or an open high-priority gap before switching")
            now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
            history = state.setdefault("mode_history", [])
            event = {"schema_version": 1, "event_id": f"MODE-{len(history) + 1:03d}", "event_type": "mode_changed",
                     "from": previous, "to": command.mode, "changed_by": command.changed_by, "changed_at": now,
                     "reason": command.reason, "operation_id": str(command.operation_id), "workflow_version": version + 1}
            history.append(event)
            state.update(mode=command.mode, updated_at=now, workflow_version=version + 1)
            return self.store.commit(project_id, command, snapshot["state"], state, snapshot["events"], event, snapshot["inputs"])
