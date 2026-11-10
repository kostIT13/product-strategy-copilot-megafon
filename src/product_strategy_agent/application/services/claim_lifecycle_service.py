"""Withdraw one claim without rewriting records, choices or prior approvals."""

from datetime import datetime, timezone
import json
from product_strategy_agent.application.ports.claim_lifecycle_store import (
    ClaimLifecycleStore,
)
from product_strategy_agent.domain.projects.claim_lifecycle import (
    ClaimWithdrawal,
    claim_impact,
    withdrawal_event,
)
from product_strategy_agent.domain.projects.workspace import validate_workspace_id
from product_strategy_agent.domain.projects.source_lifecycle import source_statuses


def rows(snapshot, name):
    values = [json.loads(line) for line in snapshot[name].splitlines() if line.strip()]
    if any(not isinstance(row, dict) for row in values):
        raise ValueError("claim lifecycle inputs must contain objects")
    return values


def impact_from_snapshot(project_id, snapshot):
    state = json.loads(snapshot["state"])
    if (
        not isinstance(state, dict)
        or state.get("schema_version") != 1
        or state.get("project_id") != project_id
        or type(state.get("workflow_version", 0)) is not int
        or state.get("workflow_version", 0) < 0
    ):
        raise ValueError("invalid claim lifecycle state")
    try:
        report = claim_impact(
            *(
                rows(snapshot, name)
                for name in ("claims", "events", "options", "decisions", "capabilities")
            )
        )
    except (KeyError, TypeError, AttributeError):
        raise ValueError("invalid claim impact inputs") from None
    return {
        "project_id": project_id,
        "workflow_version": state.get("workflow_version", 0),
        "source_statuses": source_statuses(rows(snapshot, "sources"), rows(snapshot, "events")),
        **report,
    }


class ClaimLifecycleService:
    def __init__(self, store: ClaimLifecycleStore):
        self.store = store

    def impact(self, project_id):
        validate_workspace_id(project_id)
        return impact_from_snapshot(project_id, self.store.inspect_claims(project_id))

    def withdraw(self, project_id, command):
        validate_workspace_id(project_id)
        command = ClaimWithdrawal.model_validate(command)
        with self.store.access(project_id):
            replay = self.store.replay(project_id, command)
            if replay is not None:
                return replay
            snapshot = self.store.capture_claims(project_id)
            impact = impact_from_snapshot(project_id, snapshot)
            if (
                command.expected_workflow_version is not None
                and command.expected_workflow_version != impact["workflow_version"]
            ):
                raise ValueError(
                    "expected_workflow_version conflict; review claim lifecycle"
                )
            state = json.loads(snapshot["state"])
            now = (
                datetime.now(timezone.utc)
                .isoformat(timespec="seconds")
                .replace("+00:00", "Z")
            )
            event = withdrawal_event(
                command,
                state,
                rows(snapshot, "claims"),
                rows(snapshot, "events"),
                rows(snapshot, "options"),
                rows(snapshot, "decisions"),
                rows(snapshot, "capabilities"),
                now,
            )
            after = {
                **state,
                "workflow_version": impact["workflow_version"] + 1,
                "updated_at": now,
            }
            return self.store.commit(
                project_id,
                command,
                snapshot["state"],
                after,
                snapshot["events"],
                event,
                snapshot["inputs"],
            )
