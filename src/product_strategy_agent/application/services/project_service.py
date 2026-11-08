"""Project creation and retrieval use cases."""

import re
from datetime import datetime, timezone
from uuid import uuid4

from product_strategy_agent.application.ports.project_store import ProjectStore
from product_strategy_agent.domain.projects.entities import Project
from product_strategy_agent.domain.projects.errors import (
    InvalidProject,
    ProjectNotFound,
)

_PROJECT_KEY = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")


class ProjectService:
    """Use cases for creating and retrieving full-solution projects."""

    def __init__(self, store: ProjectStore) -> None:
        self._store = store

    def create(self, key: str, name: str, description: str | None = None) -> Project:
        key = key.strip()
        name = name.strip()
        if not _PROJECT_KEY.fullmatch(key):
            raise InvalidProject("project key must be 1-64 letters, numbers, '-' or '_' and start with a letter or number")
        if not name:
            raise InvalidProject("project name must not be empty")

        now = datetime.now(timezone.utc)
        project = Project(
            id=uuid4(),
            key=key,
            name=name,
            description=description.strip() if description and description.strip() else None,
            status="active",
            created_at=now,
            updated_at=now,
        )
        return self._store.create(project)

    def get(self, key: str) -> Project:
        project = self._store.get_by_key(key)
        if project is None:
            raise ProjectNotFound(f"project '{key}' was not found")
        return project
