"""Persistence port for claims and their evidence references."""

from typing import Protocol
from uuid import UUID

from product_strategy_agent.domain.evidence.entities import Claim


class ClaimStore(Protocol):
    def create(self, claim: Claim) -> Claim: ...

    def list_for_project(self, project_key: str) -> list[Claim]: ...

    def get_project_id(self, claim_id: UUID) -> UUID | None: ...
