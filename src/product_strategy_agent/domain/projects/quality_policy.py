"""Versioned mandatory semantic-review policy and explicit legacy enablement."""

import hashlib
import json
from typing import Annotated, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from product_strategy_agent.domain.projects.claim_lifecycle import fingerprint

REQUIRED_POLICY = {"schema_version": 1, "semantic_review": "required"}


def validate_policy(value):
    if (
        not isinstance(value, dict)
        or set(value) != set(REQUIRED_POLICY)
        or type(value.get("schema_version")) is not int
        or value != REQUIRED_POLICY
    ):
        raise ValueError(
            "unknown or malformed quality_policy; explicit migration is required"
        )
    return dict(value)


def policy_required(state, events=(), initially_required=False):
    if not isinstance(state, dict) or any(not isinstance(row, dict) for row in events):
        raise ValueError("invalid quality policy state/history")
    enabled = [
        row for row in events if row.get("event_type") == "quality_policy_enabled"
    ]
    if len(enabled) > 1:
        raise ValueError("duplicate quality policy enablement history")
    for event in enabled:
        validate_policy(event.get("policy"))
    if "quality_policy" in state:
        validate_policy(state["quality_policy"])
        return True
    if initially_required or enabled:
        raise ValueError(
            "required quality_policy was removed; policy downgrade is forbidden"
        )
    return False


def snapshot_hash(state, events, inputs):
    return fingerprint(
        {
            "format_version": "psa-quality-policy-snapshot-v1",
            "state": hashlib.sha256(state).hexdigest(),
            "events": hashlib.sha256(events).hexdigest(),
            "inputs": inputs,
        }
    )


class EnableQualityPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", revalidate_instances="always")
    kind: Literal["quality_policy_enable"] = "quality_policy_enable"
    operation_id: UUID
    enabled_by: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
    ]
    reason: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)
    ]
    review_hash: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
    expected_workflow_version: int = Field(strict=True, ge=0)


def plan_enable(command, before, before_events, inputs, timestamp):
    state = json.loads(before)
    events = [json.loads(line) for line in before_events.splitlines() if line.strip()]
    if (
        not isinstance(state, dict)
        or state.get("schema_version") != 1
        or type(state.get("workflow_version", 0)) is not int
        or any(not isinstance(row, dict) for row in events)
    ):
        raise ValueError("invalid quality policy state/history")
    if policy_required(state, events):
        raise ValueError("semantic review policy is already required")
    version = state.get("workflow_version", 0)
    if (
        version < 0
        or version != command.expected_workflow_version
        or command.review_hash != snapshot_hash(before, before_events, inputs)
    ):
        raise ValueError(
            "quality policy snapshot/version/hash conflict; inspect policy show again"
        )
    event = {
        "schema_version": 1,
        "event_type": "quality_policy_enabled",
        "event_id": "POLICY-001",
        "operation_id": str(command.operation_id),
        "workflow_version": version + 1,
        "enabled_by": command.enabled_by,
        "reason": command.reason,
        "enabled_at": timestamp,
        "policy": dict(REQUIRED_POLICY),
        "review_hash": command.review_hash,
        "approvals_changed": False,
        "human_decision_changed": False,
        "workflow_approval_granted": False,
    }
    return {
        **state,
        "quality_policy": dict(REQUIRED_POLICY),
        "updated_at": timestamp,
        "workflow_version": version + 1,
    }, event
