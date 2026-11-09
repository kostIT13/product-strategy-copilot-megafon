"""Read-only file retrieval independent of CLI, MCP, SQL and model calls."""

from product_strategy_agent.application.ports.file_source_search import (
    FileSourceSearchStore,
)
from product_strategy_agent.domain.projects.file_search import (
    FileSearchRequest,
    search_snapshot,
)
from product_strategy_agent.domain.projects.workspace import validate_workspace_id


class FileSourceSearchService:
    def __init__(self, store: FileSourceSearchStore):
        self.store = store

    def search(self, project_id: str, query: str, limit: int = 10) -> dict:
        validate_workspace_id(project_id)
        request = FileSearchRequest(query=query, limit=limit)
        return search_snapshot(project_id, request, self.store.snapshot(project_id))
