"""Claim evidence references tied to immutable source revisions."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class EvidenceReference:
    source_id: UUID
    source_revision: int
    locator: str
    quote: str


@dataclass(frozen=True, slots=True)
class Claim:
    id: UUID
    project_id: UUID
    key: str
    text: str
    claim_type: str
    confidence: str
    reasoning_note: str | None
    decision_impact: str | None
    status: str
    created_at: datetime
    evidence: tuple[EvidenceReference, ...]
