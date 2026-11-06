"""Persistence port for claims and their evidence references."""

from typing import Protocol

from product_strategy_agent.domain.evidence.entities import Claim


class ClaimStore(Protocol):
    def create(self, claim: Claim) -> Claim: ...

    def list_for_project(self, project_key: str) -> list[Claim]: ...
