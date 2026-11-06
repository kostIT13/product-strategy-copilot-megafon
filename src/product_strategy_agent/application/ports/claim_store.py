"""Persistence port for claims and their evidence references."""

from typing import Protocol
from uuid import UUID

from product_strategy_agent.domain.evidence.entities import Claim, ClaimReferenceInfo


class ClaimStore(Protocol):
    def create(self, claim: Claim) -> Claim: ...

    def list_for_project(self, project_key: str) -> list[Claim]: ...

    def get_reference_info(self, claim_id: UUID) -> ClaimReferenceInfo | None: ...
