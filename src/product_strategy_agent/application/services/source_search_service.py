"""Validate retrieval requests without depending on PostgreSQL."""

from product_strategy_agent.application.ports.source_search import SourceSearch
from product_strategy_agent.domain.sources.search import SourceSearchHit


class SourceSearchService:
    def __init__(self, search: SourceSearch):
        self._search = search

    def search(self, project_key: str, query: str, limit: int = 10) -> list[SourceSearchHit]:
        project_key, query = project_key.strip(), query.strip()
        if not project_key:
            raise ValueError("project key must not be empty")
        if not query or len(query) > 1000 or not any(char.isalnum() for char in query):
            raise ValueError("search query needs a word or number and must be at most 1000 characters")
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 50:
            raise ValueError("search limit must be an integer between 1 and 50")
        return self._search.search(project_key, query, limit)
