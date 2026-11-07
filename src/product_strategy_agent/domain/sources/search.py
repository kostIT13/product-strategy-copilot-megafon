"""Search results with stable references to source revisions."""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class SourceSearchHit:
    source_id: UUID
    revision_id: UUID
    revision: int
    uri: str
    title: str
    content_hash: str
    locator: str
    score: float
    excerpt: str
