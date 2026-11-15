"""Immutable local task/result records, not canonical facts or authenticated execution."""

import json
from typing import Annotated, Literal
from uuid import UUID
from pydantic import (
    AwareDatetime,
    Field,
    TypeAdapter,
    ValidationError,
    field_validator,
    model_validator,
)
from product_strategy_agent.domain.automation.contracts import (
    Digest,
    Identifier,
    Model,
    Packet,
    Text,
    fingerprint,
)
from product_strategy_agent.domain.automation.handoffs import (
    Handoff,
    PrepareHandoff,
    TaskGoal,
    strict_json,
    validation_message,
)
from product_strategy_agent.domain.automation.subagents import (
    SubagentResult,
    validate_result_binding,
)


def handoff_model(packet):
    body = dict(packet)
    expected_handoff = body.pop("handoff_fingerprint", None)
    expected_task = body.pop("task_fingerprint", None)
    if (
        body.pop("execution_started", None) is not False
        or body.pop("canonical_writes", None) is not False
    ):
        raise ValueError("handoff flags do not describe read-only preparation")
    handoff = Handoff.model_validate_json(
        json.dumps(body, ensure_ascii=False, allow_nan=False)
    )
    if (
        fingerprint(handoff) != expected_handoff
        or fingerprint(handoff.task) != expected_task
    ):
        raise ValueError("handoff fingerprint mismatch")
    return handoff


def handoff_output(handoff):
    return {
        **handoff.model_dump(mode="json"),
        "handoff_fingerprint": fingerprint(handoff),
        "task_fingerprint": fingerprint(handoff.task),
        "execution_started": False,
        "canonical_writes": False,
    }


class RecordResult(Packet):
    operation_id: UUID
    task_id: UUID
    expected_task_fingerprint: Digest
    submitted_by: Annotated[str, Field(min_length=1, max_length=200)]
    result: SubagentResult

    @model_validator(mode="after")
    def bound_command(self):
        if (
            not self.submitted_by.strip()
            or self.task_id != self.result.task_id
            or self.expected_task_fingerprint != self.result.task_fingerprint
        ):
            raise ValueError("invalid result submitter or task binding")
        return self


def parse_result_request(raw):
    try:
        return RecordResult.model_validate_json(
            json.dumps(strict_json(raw), ensure_ascii=False, allow_nan=False)
        )
    except ValidationError as error:
        raise ValueError(validation_message(error)) from None


class ReviewResult(Packet):
    operation_id: UUID
    task_id: UUID
    result_operation_id: UUID
    expected_result_record_hash: Digest
    reviewed_by: Annotated[str, Field(min_length=1, max_length=200)]
    reason: Text
    verdict: Literal["ready_for_followup", "changes_requested", "rejected"]
    finding_indices: list[Annotated[int, Field(ge=0, le=31)]] = Field(
        default_factory=list, max_length=32
    )

    @model_validator(mode="after")
    def selections(self):
        if not self.reviewed_by.strip() or len(set(self.finding_indices)) != len(
            self.finding_indices
        ):
            raise ValueError("invalid result reviewer/finding indices")
        if self.verdict != "ready_for_followup" and self.finding_indices:
            raise ValueError("non-ready review cannot select findings")
        return self


def parse_review_request(raw):
    try:
        return ReviewResult.model_validate_json(
            json.dumps(strict_json(raw), ensure_ascii=False, allow_nan=False)
        )
    except ValidationError as error:
        raise ValueError(validation_message(error)) from None


class RecordBase(Model):
    schema_version: Literal[1] = Field(...)
    project_id: Identifier
    recorded_at: AwareDatetime

    @field_validator("schema_version", mode="before")
    @classmethod
    def exact_version(cls, value):
        if type(value) is not int or value != 1:
            raise ValueError("task journal schema_version must be integer 1")
        return value

    @model_validator(mode="after")
    def bounded(self):
        if (
            len(
                json.dumps(self.model_dump(mode="json"), ensure_ascii=False).encode(
                    "utf-8"
                )
            )
            > 256000
        ):
            raise ValueError("task journal record exceeds 256000 bytes")
        return self


class TaskRegistration(RecordBase):
    kind: Literal["task"] = "task"
    registered_by: Annotated[str, Field(min_length=1, max_length=200)]
    request: PrepareHandoff
    handoff: Handoff

    @model_validator(mode="after")
    def reconstruct(self):
        task = self.handoff.task
        if (
            not self.registered_by.strip()
            or self.project_id != task.target.project_id
            or (self.request.task_id, self.request.role, self.request.budget)
            != (task.task_id, task.role, task.budget)
        ):
            raise ValueError("registered task request/target mismatch")
        goal = TaskGoal.model_validate_json(task.goal)
        if self.request.goal != goal.requested_goal or len(
            self.request.selections
        ) != len(self.handoff.origins):
            raise ValueError("registered task goal/selection mismatch")
        for selection, origin in zip(self.request.selections, self.handoff.origins):
            if (selection.input_id, selection.path, selection.start) != (
                origin.input_id,
                origin.path,
                origin.start,
            ) or (selection.end is not None and selection.end != origin.end):
                raise ValueError("registered task origin differs from request")
        return self


class ResultRegistration(RecordBase):
    kind: Literal["result"] = "result"
    parent_record_hash: Digest
    command: RecordResult

    @model_validator(mode="after")
    def same_case(self):
        if self.project_id != self.command.result.target.project_id:
            raise ValueError("result belongs to another case")
        return self


class ReviewRegistration(RecordBase):
    kind: Literal["review"] = "review"
    command: ReviewResult


RecordAdapter = TypeAdapter(
    Annotated[
        TaskRegistration | ResultRegistration | ReviewRegistration,
        Field(discriminator="kind"),
    ]
)


def load_record(raw, project_id, kind, identifier):
    envelope = strict_json(raw)
    if not isinstance(envelope, dict) or set(envelope) != {"record", "record_hash"}:
        raise ValueError("invalid task journal envelope")
    try:
        record = RecordAdapter.validate_json(
            json.dumps(envelope["record"], ensure_ascii=False, allow_nan=False)
        )
    except ValidationError:
        raise ValueError("invalid task journal record schema") from None
    own_id = (
        record.request.task_id
        if isinstance(record, TaskRegistration)
        else record.command.operation_id
    )
    if (
        record.project_id != project_id
        or record.kind != kind
        or own_id != identifier
        or fingerprint(record) != envelope["record_hash"]
    ):
        raise ValueError("task journal identity/hash mismatch")
    return record


def validate_parent(task, result):
    if (
        result.parent_record_hash != fingerprint(task)
        or result.command.task_id != task.request.task_id
    ):
        raise ValueError("result parent record mismatch")
    validate_result_binding(task.handoff.task, result.command.result)


def validate_review_parent(result, review):
    command = review.command
    body = result.command.result
    if (
        review.project_id != result.project_id
        or command.task_id != result.command.task_id
        or command.result_operation_id != result.command.operation_id
        or command.expected_result_record_hash != fingerprint(result)
    ):
        raise ValueError("review result parent mismatch")
    if command.verdict == "ready_for_followup" and (
        body.outcome != "completed"
        or any(index >= len(body.findings) for index in command.finding_indices)
    ):
        raise ValueError(
            "ready review requires completed result and valid finding indices"
        )


def encode_record(record):
    data = (
        json.dumps(
            {
                "record": record.model_dump(mode="json"),
                "record_hash": fingerprint(record),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")
    if len(data) > 256000:
        raise ValueError("task journal envelope exceeds 256000 bytes")
    return data


def receipt(record):
    task = isinstance(record, TaskRegistration)
    result = isinstance(record, ResultRegistration)
    return {
        "format_version": "psa-subagent-journal-v1",
        "project_id": record.project_id,
        "kind": record.kind,
        "record_hash": fingerprint(record),
        "recorded_at": record.recorded_at.isoformat(),
        "recorded_by": record.registered_by
        if task
        else record.command.submitted_by
        if result
        else record.command.reviewed_by,
        "task_id": str(record.request.task_id if task else record.command.task_id),
        "operation_id": None if task else str(record.command.operation_id),
        "task_fingerprint": fingerprint(record.handoff.task)
        if task
        else record.command.expected_task_fingerprint
        if result
        else None,
        "outcome": record.command.result.outcome if result else None,
        "verdict": record.command.verdict
        if isinstance(record, ReviewRegistration)
        else None,
        "requires_review": True,
        "identity_verified": False,
        "execution_verified": False,
        "canonical_adoption": False,
        "workflow_approval_granted": False,
    }
