"""Persistence port for workflow state and append-only events."""

from typing import Protocol
from uuid import UUID

from product_strategy_agent.domain.workflow.entities import (
    GateCounts,
    WorkflowEvent,
    WorkflowState,
)


class WorkflowStore(Protocol):
    def start(self, project_id: UUID, actor: str, reason: str) -> WorkflowState: ...

    def get_state(self, project_id: UUID) -> WorkflowState | None: ...

    def get_gate_counts(self, project_id: UUID) -> GateCounts: ...

    def advance(
        self,
        project_id: UUID,
        expected_version: int,
        to_stage: str,
        actor: str,
        reason: str,
    ) -> WorkflowState: ...

    def list_events(self, project_id: UUID) -> list[WorkflowEvent]: ...
