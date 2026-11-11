"""Deliberate pre-policy cases for historical behavior tests, never a public bypass."""

from datetime import datetime, timezone
from uuid import uuid4
from product_strategy_agent.adapters.persistence.files.workspace_repository import (
    FileWorkspaceStore,
)
from product_strategy_agent.domain.projects.workspace import workspace_seed


def init_legacy_project(project_id, root):
    timestamp = (
        datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    )
    return FileWorkspaceStore(root).create(
        workspace_seed(project_id, timestamp), uuid4()
    )
