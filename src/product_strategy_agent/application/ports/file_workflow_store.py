"""Inspection/recovery boundary for already human-authorized workflow operations."""
from typing import Protocol
from uuid import UUID


class WorkflowStore(Protocol):
    def pending(self, project_id: str) -> dict: ...
    def recover(self, project_id: str, operation_id: UUID) -> dict: ...
