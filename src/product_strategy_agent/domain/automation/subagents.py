"""Bounded data handoffs and result binding, without model calls or case writes."""

import hashlib
from decimal import Decimal
from typing import Literal
from uuid import UUID
from pydantic import Field, model_validator
from product_strategy_agent.domain.automation.contracts import (
    Budget,
    CaseTarget,
    Cost,
    Digest,
    Identifier,
    Model,
    Packet,
    Text,
    fingerprint,
)

Role = Literal["research", "evidence", "critic"]


class Excerpt(Model):
    input_id: Identifier
    text: str = Field(min_length=1, max_length=16000)
    sha256: Digest

    @model_validator(mode="after")
    def exact_hash(self):
        if hashlib.sha256(self.text.encode("utf-8")).hexdigest() != self.sha256:
            raise ValueError("excerpt sha256 does not match exact UTF-8 text")
        return self


class SubagentTask(Packet):
    task_id: UUID
    role: Role
    target: CaseTarget
    goal: Text
    budget: Budget
    inputs: list[Excerpt] = Field(min_length=1, max_length=16)

    @model_validator(mode="after")
    def distinct_inputs(self):
        ids = [row.input_id for row in self.inputs]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate input IDs")
        return self


class Finding(Model):
    kind: Literal["observation", "hypothesis", "question", "risk"]
    text: Text
    evidence_input_ids: list[Identifier] = Field(default_factory=list, max_length=16)

    @model_validator(mode="after")
    def evidence(self):
        if self.kind == "observation" and not self.evidence_input_ids:
            raise ValueError("observation requires input references")
        if len(self.evidence_input_ids) != len(set(self.evidence_input_ids)):
            raise ValueError("duplicate finding input references")
        return self


class Usage(Model):
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    duration_ms: int | None = Field(default=None, ge=0)
    cost: Cost | None = None
    currency: Literal["RUB", "USD"] | None = None

    @model_validator(mode="after")
    def cost_pair(self):
        if (self.cost is None) != (self.currency is None):
            raise ValueError("usage currency and cost must be specified together")
        return self


class SubagentResult(Packet):
    task_id: UUID
    role: Role
    target: CaseTarget
    task_fingerprint: Digest
    outcome: Literal["completed", "failed", "cancelled", "budget_exceeded"]
    findings: list[Finding] = Field(default_factory=list, max_length=32)
    reason: Text | None = None
    usage: Usage = Field(default_factory=Usage)

    @model_validator(mode="after")
    def outcome_consistency(self):
        if self.outcome != "completed" and (not self.reason or self.findings):
            raise ValueError(
                "unsuccessful result requires reason and no partial findings"
            )
        if self.outcome == "completed" and self.reason is not None:
            raise ValueError("completed result cannot carry a failure reason")
        return self


def validate_result_binding(task, result):
    task = SubagentTask.model_validate(task)
    result = SubagentResult.model_validate(result)
    if (result.task_id, result.role, result.target, result.task_fingerprint) != (
        task.task_id,
        task.role,
        task.target,
        fingerprint(task),
    ):
        raise ValueError("subagent result does not match exact task/snapshot")
    allowed = {row.input_id for row in task.inputs}
    if any(
        not set(row.evidence_input_ids).issubset(allowed) for row in result.findings
    ):
        raise ValueError("finding references input not supplied to task")
    usage = result.usage
    over_budget = sum(
        value
        for value in (usage.input_tokens, usage.output_tokens)
        if value is not None
    ) > task.budget.token_limit or (
        usage.duration_ms is not None
        and usage.duration_ms > task.budget.timeout_seconds * 1000
    )
    if task.budget.max_cost is not None:
        comparable = usage.cost is not None and usage.currency == task.budget.currency
        if result.outcome == "completed" and not comparable:
            raise ValueError("completed result cannot verify declared cost cap")
        if comparable and Decimal(usage.cost) > Decimal(task.budget.max_cost):
            over_budget = True
    if over_budget and result.outcome != "budget_exceeded":
        raise ValueError(
            "reported usage exceeds budget; expected budget_exceeded outcome"
        )
    return result
