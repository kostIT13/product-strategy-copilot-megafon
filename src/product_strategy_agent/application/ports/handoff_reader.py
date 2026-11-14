"""Read only selected case text and trusted role guidance, never run a role."""

from typing import Protocol
from product_strategy_agent.domain.automation.handoffs import (
    HandoffSnapshot,
    RoleProfile,
)


class HandoffReader(Protocol):
    def read(self, project_id: str, selections) -> HandoffSnapshot: ...


class RoleInstructionReader(Protocol):
    def read(self, role: str) -> RoleProfile: ...
