"""Workspace creation/recovery port; initial publication is one indivisible operation."""
from pathlib import Path
from typing import Protocol
from uuid import UUID
from product_strategy_agent.domain.projects.workspace import WorkspaceSeed


class WorkspaceStore(Protocol):
    def create(self, seed: WorkspaceSeed, operation_id: UUID) -> Path: ...

    def pending(self, project_id: str) -> list[dict]: ...

    def recover(self, project_id: str, operation_id: UUID) -> Path: ...
