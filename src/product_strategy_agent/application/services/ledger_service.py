"""Append one validated record without double insertion or resetting later edits."""

from datetime import datetime, timezone
import json
from product_strategy_agent.application.ports.ledger_store import LedgerStore
from product_strategy_agent.domain.projects.ledger_append import LedgerAppend
from product_strategy_agent.domain.projects.workspace import validate_workspace_id
from product_strategy_agent.domain.projects.claim_lifecycle import require_active_support


class LedgerService:
    def __init__(self, store: LedgerStore):
        self.store = store

    def append(self, project_id, command):
        project_id = validate_workspace_id(project_id)
        command = LedgerAppend.model_validate(command)
        with self.store.access(project_id):
            replay = self.store.replay(project_id, command)
            if replay is not None:
                return replay
            snapshot = self.store.capture_ledger(project_id, command.ledger)
            state = json.loads(snapshot["state"])
            version = state.get("workflow_version", 0)
            if (
                state.get("schema_version") != 1
                or state.get("project_id") != project_id
                or type(version) is not int
                or version < 0
            ):
                raise ValueError("invalid ledger workflow state")
            if (
                command.expected_workflow_version is not None
                and command.expected_workflow_version != version
            ):
                raise ValueError(
                    "expected_workflow_version conflict; review the current ledgers"
                )
            require_active_support(command.ledger, command.payload, snapshot["ledger_inputs"],
                                   [json.loads(line) for line in snapshot["events"].splitlines() if line.strip()])
            now = (
                datetime.now(timezone.utc)
                .isoformat(timespec="seconds")
                .replace("+00:00", "Z")
            )
            return self.store.commit_ledger(project_id, command, snapshot, now)
