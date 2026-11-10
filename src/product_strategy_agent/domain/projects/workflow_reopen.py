"""Explicit reopening of a completed workflow; prior approvals remain history."""

from copy import deepcopy
import hashlib
import json
from typing import Annotated, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from product_strategy_agent.domain.workflow.entities import WORKFLOW_STAGES
from product_strategy_agent.domain.projects.claim_lifecycle import fingerprint

ReopenStage = Literal[
    "intake",
    "research_plan",
    "source_collection",
    "evidence_review",
    "options",
    "strategy",
    "validation",
]


class WorkflowReopen(BaseModel):
    model_config = ConfigDict(extra="forbid", revalidate_instances="always")
    kind: Literal["workflow_reopen"] = "workflow_reopen"
    operation_id: UUID
    target_stage: ReopenStage
    reopened_by: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
    ]
    reason: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)
    ]
    review_hash: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
    expected_workflow_version: int = Field(strict=True, ge=0)


def review_hash(state, events, inputs):
    return fingerprint(
        {
            "format_version": "psa-workflow-review-v1",
            "state": hashlib.sha256(state).hexdigest(),
            "events": hashlib.sha256(events).hexdigest(),
            "inputs": inputs,
        }
    )


def plan_reopen(command, before, before_events, inputs, timestamp):
    state = json.loads(before)
    if not isinstance(state, dict) or state.get("schema_version") != 1:
        raise ValueError("invalid workflow reopen state")
    if state.get("status") != "completed":
        raise ValueError("only a completed workflow can be reopened")
    version = state.get("workflow_version", 0)
    if (
        type(version) is not int
        or version < 0
        or version != command.expected_workflow_version
    ):
        raise ValueError("expected_workflow_version conflict; review current workflow")
    if command.review_hash != review_hash(before, before_events, inputs):
        raise ValueError("review_hash conflict; inspect workflow review again")
    stages = state.get("stages")
    if (
        not isinstance(stages, dict)
        or set(stages) != set(WORKFLOW_STAGES)
        or any(value != "done" for value in stages.values())
    ):
        raise ValueError("completed workflow requires all stages done before reopening")
    approvals = state.get("approvals", [])
    history = state.get("reopen_history", [])
    if (
        not isinstance(approvals, list)
        or any(
            not isinstance(row, dict) or not isinstance(row.get("event_id"), str)
            for row in approvals
        )
        or not isinstance(history, list)
        or any(not isinstance(row, dict) for row in history)
    ):
        raise ValueError("invalid workflow approval/reopen history")
    invalidated = list(WORKFLOW_STAGES[WORKFLOW_STAGES.index(command.target_stage) :])
    event = {
        "schema_version": 1,
        "event_type": "workflow_reopened",
        "event_id": f"REOPEN-{len(history) + 1:03d}",
        "operation_id": str(command.operation_id),
        "workflow_version": version + 1,
        "from": "completed",
        "target_stage": command.target_stage,
        "reopened_by": command.reopened_by,
        "reason": command.reason,
        "reopened_at": timestamp,
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
        updated_at=timestamp,
        workflow_version=version + 1,
        next_action=f"Пересмотреть этап {command.target_stage}; пройти повторные human gates",
        reopen_history=[*history, event],
    )
    return after, event
