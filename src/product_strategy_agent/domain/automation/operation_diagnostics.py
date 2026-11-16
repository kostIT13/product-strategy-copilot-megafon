"""Text-free historical operation facts; never infer execution or measured usage."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

from product_strategy_agent.domain.automation.contracts import (
    CaseTarget,
    Identifier,
    Packet,
)
from product_strategy_agent.domain.automation.subagents import Usage

OperationKind = Literal["task", "result", "review", "hook"]
Publication = Literal[
    "published",
    "prepared",
    "execution_unknown",
    "result_prepared",
    "completion_recorded",
]


class DiagnoseOperation(Packet):
    project_id: Identifier
    kind: OperationKind
    operation_id: UUID


@dataclass(frozen=True)
class OperationFacts:
    publication: Publication
    schema_version: int
    record_hash: str
    target: CaseTarget
    recorded_at: datetime | None = None
    task_id: UUID | None = None
    parent_record_hash: str | None = None
    outcome: str | None = None
    outcome_provenance: str | None = None
    review_verdict: str | None = None
    completion_hash: str | None = None
    completion_kind: str | None = None
    usage: Usage | None = None


def usage_diagnostics(usage):
    def metric(value, unit):
        return {
            "value": value,
            "unit": unit,
            "basis": "unknown",
            "provenance": "self_reported" if value is not None else "unavailable",
            "verified": False,
        }

    return {
        "input_tokens": metric(usage.input_tokens if usage else None, "tokens"),
        "output_tokens": metric(usage.output_tokens if usage else None, "tokens"),
        "duration_ms": metric(usage.duration_ms if usage else None, "ms"),
        "cost": metric(
            usage.cost if usage else None, usage.currency if usage else None
        ),
    }
