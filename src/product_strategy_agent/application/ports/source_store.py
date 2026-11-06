"""Persistence port for sources and immutable revisions."""

from typing import Protocol

from product_strategy_agent.domain.sources.entities import (
    Source,
    SourceRegistration,
    SourceRevisionDraft,
)


class SourceStore(Protocol):
    def register_revision(
        self,
        project_key: str,
        uri: str,
        kind: str,
        publisher: str | None,
        revision: SourceRevisionDraft,
    ) -> SourceRegistration: ...

    def list_for_project(self, project_key: str) -> list[Source]: ...
