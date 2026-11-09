"""A coherent, checked current-text snapshot; no acquisition or index writes."""

from typing import Protocol
from product_strategy_agent.domain.projects.file_search import SearchSnapshot


class FileSourceSearchStore(Protocol):
    def snapshot(self, project_id: str) -> SearchSnapshot: ...
