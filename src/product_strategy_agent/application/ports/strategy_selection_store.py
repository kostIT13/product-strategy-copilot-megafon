"""Atomic persistence of reviewed alternatives, decision and provenance."""
from typing import Protocol
from uuid import UUID
from product_strategy_agent.domain.decisions.selection import SelectionCommand


class StrategySelectionStore(Protocol):
    def get(self, project_id: UUID, source_run_id: UUID) -> dict | None: ...

    def record(self, project_id: UUID, command: SelectionCommand, request_hash: str, preview: dict) -> dict: ...
