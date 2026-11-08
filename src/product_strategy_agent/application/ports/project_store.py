"""Persistence port for project use cases."""

from typing import Protocol

from product_strategy_agent.domain.projects.entities import Project


class ProjectStore(Protocol):
    def create(self, project: Project) -> Project: ...

    def get_by_key(self, key: str) -> Project | None: ...
