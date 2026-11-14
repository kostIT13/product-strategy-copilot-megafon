"""Explicit backward transition of active work, preserving evidence and prior choices."""

from copy import deepcopy
import json
from typing import Annotated, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from product_strategy_agent.domain.workflow.entities import WORKFLOW_STAGES
from product_strategy_agent.domain.projects.workflow_reopen import (
    ReopenStage,
    review_hash,
)


class WorkflowRollback(BaseModel):
    model_config = ConfigDict(extra="forbid", revalidate_instances="always")
    kind: Literal["workflow_rollback"] = "workflow_rollback"
    operation_id: UUID
    target_stage: ReopenStage
    rolled_back_by: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
    ]
    reason: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)
    ]
    review_hash: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
    expected_workflow_version: int = Field(strict=True, ge=0)


def plan_rollback(command, before, before_events, inputs, timestamp):
    state = json.loads(before)
    if not isinstance(state, dict) or state.get("schema_version") != 1:
        raise ValueError("invalid workflow rollback state")
    current = state.get("status")
    if current not in WORKFLOW_STAGES[:-1]:
        raise ValueError(
            "rollback requires an active workflow; use reopen for completed work"
        )
    current_index = WORKFLOW_STAGES.index(current)
    target_index = WORKFLOW_STAGES.index(command.target_stage)
    if target_index >= current_index:
        raise ValueError("rollback target must precede the current stage")
    version = state.get("workflow_version", 0)
    if (
        type(version) is not int
        or version < 0
        or version != command.expected_workflow_version
    ):
        raise ValueError("expected_workflow_version conflict; review current workflow")
    if command.review_hash != review_hash(before, before_events, inputs):
        raise ValueError("review_hash conflict; inspect workflow review again")
    expected_stages = {
        stage: "done"
        if index < current_index
        else "in_progress"
        if index == current_index
        else "not_started"
        for index, stage in enumerate(WORKFLOW_STAGES)
    }
    if state.get("stages") != expected_stages:
        raise ValueError("active workflow stages are inconsistent")
    approvals = state.get("approvals", [])
    history = state.get("rollback_history", [])
    if (
        not isinstance(approvals, list)
        or any(
            not isinstance(row, dict) or not isinstance(row.get("event_id"), str)
            for row in approvals
        )
        or not isinstance(history, list)
        or any(not isinstance(row, dict) for row in history)
    ):
        raise ValueError("invalid workflow approval/rollback history")
    invalidated = list(WORKFLOW_STAGES[target_index:])
    event = {
        "schema_version": 1,
        "event_type": "workflow_rolled_back",
        "event_id": f"ROLLBACK-{len(history) + 1:03d}",
        "operation_id": str(command.operation_id),
        "workflow_version": version + 1,
        "from": current,
        "target_stage": command.target_stage,
        "rolled_back_by": command.rolled_back_by,
        "reason": command.reason,
        "rolled_back_at": timestamp,
        "review_hash": command.review_hash,
        "invalidated_stages": invalidated,
        "historical_approval_ids": [
            row["event_id"] for row in approvals if row.get("stage") in invalidated
        ],
        "human_decision_changed": False,
        "new_approval_granted": False,
    }
    after = deepcopy(state)
    for stage in invalidated:
        after["stages"][stage] = (
            "in_progress" if stage == command.target_stage else "not_started"
        )
    after.update(
        status=command.target_stage,
        workflow_version=version + 1,
        updated_at=timestamp,
        next_action=f"Пересмотреть этап {command.target_stage}; пройти повторные human gates",
        rollback_history=[*history, event],
    )
    return after, event
