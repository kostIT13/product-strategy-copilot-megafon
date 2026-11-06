"""Source records and immutable extracted-text revisions."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class SourceRevisionDraft:
    title: str
    content_hash: str
    extracted_text: str
    locator: str
    accessed_at: datetime
    limitations: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SourceRevision:
    id: UUID
    source_id: UUID
    revision: int
    title: str
    content_hash: str
    extracted_text: str
    locator: str
    accessed_at: datetime
    limitations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Source:
    id: UUID
    project_id: UUID
    uri: str
    kind: str
    publisher: str | None
    reliability: str
    status: str
    revision: SourceRevision


@dataclass(frozen=True, slots=True)
class SourceRegistration:
    source: Source
    created_revision: bool
