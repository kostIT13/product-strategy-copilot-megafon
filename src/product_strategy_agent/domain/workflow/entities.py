"""Ordered project stages and immutable transition events."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

WORKFLOW_STAGES = (
    "intake",
    "research_plan",
    "source_collection",
    "evidence_review",
    "options",
    "strategy",
    "validation",
    "completed",
)


@dataclass(frozen=True, slots=True)
class WorkflowState:
    project_id: UUID
    current_stage: str
    status: str
    version: int
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class WorkflowEvent:
    id: UUID
    project_id: UUID
    sequence: int
    event_type: str
    from_stage: str | None
    to_stage: str
    actor: str
    reason: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class GateCounts:
    sources: int
    claims: int
    factual_claims: int
    options: int
    decisions: int
