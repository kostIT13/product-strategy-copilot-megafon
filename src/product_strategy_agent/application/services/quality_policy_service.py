"""Inspect policy and explicitly migrate a reviewed legacy snapshot, without reapprovals."""

from datetime import datetime, timezone
import json
from product_strategy_agent.application.ports.quality_policy_store import (
    QualityPolicyStore,
)
from product_strategy_agent.domain.projects.quality_policy import (
    EnableQualityPolicy,
    policy_required,
    plan_enable,
    snapshot_hash,
)
from product_strategy_agent.domain.projects.workspace import validate_workspace_id


def policy_report(project_id, snapshot):
    state = json.loads(snapshot["state"])
    events = [
        json.loads(line) for line in snapshot["events"].splitlines() if line.strip()
    ]
    if (
        not isinstance(state, dict)
        or state.get("schema_version") != 1
        or state.get("project_id") != project_id
        or type(state.get("workflow_version", 0)) is not int
        or state.get("workflow_version", 0) < 0
        or any(not isinstance(row, dict) for row in events)
    ):
        raise ValueError("invalid policy inspection state/history")
    required = policy_required(state, events, snapshot["initially_required"])
    return {
        "format_version": "psa-quality-policy-v1",
        "project_id": project_id,
        "workflow_version": state.get("workflow_version", 0),
        "status": state["status"],
        "mode": "semantic_required_v1" if required else "legacy_adoption",
        "policy": state.get("quality_policy"),
        "initially_required": snapshot["initially_required"],
        "enablement_history": [
            row for row in events if row.get("event_type") == "quality_policy_enabled"
        ],
        "semantic_audit_scopes": sorted(
            {
                row["scope"]
                for row in events
                if row.get("event_type") == "semantic_review_recorded"
            }
        ),
        "historical_approval_count": len(state.get("approvals", [])),
        "review_hash": snapshot_hash(
            snapshot["state"], snapshot["events"], snapshot["inputs"]
        ),
        "workflow_approval_granted": False,
    }


class QualityPolicyService:
    def __init__(self, store: QualityPolicyStore):
        self.store = store

    def show(self, project_id):
        validate_workspace_id(project_id)
        with self.store.access(project_id):
            return policy_report(project_id, self.store.capture(project_id))

    def enable(self, project_id, command):
        validate_workspace_id(project_id)
        command = EnableQualityPolicy.model_validate(command)
        with self.store.access(project_id):
            replay = self.store.replay(project_id, command)
            if replay is not None:
                return replay
            snapshot = self.store.capture(project_id)
            report = policy_report(project_id, snapshot)
            if report["mode"] != "legacy_adoption":
                raise ValueError("semantic review policy is already required")
            timestamp = (
                datetime.now(timezone.utc)
                .isoformat(timespec="seconds")
                .replace("+00:00", "Z")
            )
            after, event = plan_enable(
                command,
                snapshot["state"],
                snapshot["events"],
                snapshot["inputs"],
                timestamp,
            )
            return self.store.commit(
                project_id,
                command,
                {**snapshot, "after": after, "event": event},
                timestamp,
            )
