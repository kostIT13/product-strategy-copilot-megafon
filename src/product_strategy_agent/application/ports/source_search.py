"""Port for project-scoped retrieval of current source revisions."""

from typing import Protocol
from product_strategy_agent.domain.sources.search import SourceSearchHit


class SourceSearch(Protocol):
    def search(self, project_key: str, query: str, limit: int) -> list[SourceSearchHit]: ...
