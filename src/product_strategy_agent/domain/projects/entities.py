"""Project entity independent of persistence and interfaces."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Project:
    id: UUID
    key: str
    name: str
    description: str | None
    status: str
    created_at: datetime
    updated_at: datetime
