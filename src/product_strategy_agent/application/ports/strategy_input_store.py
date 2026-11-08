"""Immutable context snapshots for decision-bound model requests."""
from typing import Protocol
from uuid import UUID


class StrategyInputStore(Protocol):
    def put(self, project_id: UUID, input_hash: str, snapshot: dict) -> None: ...
    def get(self, project_id: UUID, input_hash: str) -> dict | None: ...
