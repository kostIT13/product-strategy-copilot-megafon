"""Withdraw only on explicit human instruction, without acquisition or record rewriting."""

from datetime import datetime, timezone
import json
from product_strategy_agent.application.ports.source_lifecycle_store import (
    SourceLifecycleStore,
)
from product_strategy_agent.domain.projects.source_lifecycle import (
    SourceWithdrawal,
    source_impact,
    plan_withdrawal,
)
from product_strategy_agent.domain.projects.workspace import validate_workspace_id


def state_from_snapshot(project_id, snapshot):
    state = json.loads(snapshot["state"])
    if (
        not isinstance(state, dict)
        or state.get("schema_version") != 1
        or state.get("project_id") != project_id
        or type(state.get("workflow_version", 0)) is not int
        or state.get("workflow_version", 0) < 0
    ):
        raise ValueError("invalid source lifecycle state")
    return state


class SourceLifecycleService:
    def __init__(self, store: SourceLifecycleStore):
        self.store = store

    def impact(self, project_id):
        validate_workspace_id(project_id)
        with self.store.access(project_id):
            snapshot = self.store.capture_sources(project_id)
            state = state_from_snapshot(project_id, snapshot)
            events = [
                json.loads(line)
                for line in snapshot["events"].splitlines()
                if line.strip()
            ]
            return {
                "project_id": project_id,
                "workflow_version": state.get("workflow_version", 0),
                **source_impact(snapshot["ledger_inputs"], events),
            }

    def withdraw(self, project_id, command):
        validate_workspace_id(project_id)
        command = SourceWithdrawal.model_validate(command)
        with self.store.access(project_id):
            replay = self.store.replay(project_id, command)
            if replay is not None:
                return replay
            snapshot = self.store.capture_sources(project_id)
            state = state_from_snapshot(project_id, snapshot)
            if (
                command.expected_workflow_version is not None
                and command.expected_workflow_version
                != state.get("workflow_version", 0)
            ):
                raise ValueError(
                    "expected_workflow_version conflict; inspect source impact"
                )
            now = (
                datetime.now(timezone.utc)
                .isoformat(timespec="seconds")
                .replace("+00:00", "Z")
            )
            plan_withdrawal(
                command,
                state,
                snapshot["ledger_inputs"],
                [
                    json.loads(line)
                    for line in snapshot["events"].splitlines()
                    if line.strip()
                ],
                now,
            )
            return self.store.commit_source_withdrawal(
                project_id, command, snapshot, now
            )
