"""Alternatives and recorded human decisions."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class OptionClaim:
    claim_id: UUID
    relation: str


@dataclass(frozen=True, slots=True)
class StrategicOption:
    id: UUID
    project_id: UUID
    key: str
    name: str
    description: str | None
    strengths: tuple[str, ...]
    risks: tuple[str, ...]
    assumptions: tuple[str, ...]
    claim_links: tuple[OptionClaim, ...]
    status: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class DecisionAlternative:
    option_id: UUID
    disposition: str


@dataclass(frozen=True, slots=True)
class Decision:
    id: UUID
    project_id: UUID
    key: str
    selected_option_id: UUID
    owner: str
    rationale: str
    assumptions: tuple[str, ...]
    risks: tuple[str, ...]
    review_trigger: str
    decided_at: datetime
    basis_claim_ids: tuple[UUID, ...]
    alternatives: tuple[DecisionAlternative, ...]
