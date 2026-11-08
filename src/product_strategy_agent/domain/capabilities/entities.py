"""Product capabilities and their factual support."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Capability:
    id: UUID
    project_id: UUID
    key: str
    name: str
    description: str | None
    status: str
    claim_ids: tuple[UUID, ...]
    created_at: datetime
