"""Persistence port for immutable decision records."""

from typing import Protocol

from product_strategy_agent.domain.decisions.entities import Decision


class DecisionStore(Protocol):
    def create(self, decision: Decision) -> Decision: ...

    def list_for_project(self, project_key: str) -> list[Decision]: ...
