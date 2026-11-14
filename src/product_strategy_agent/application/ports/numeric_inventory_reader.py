"""A coherent read-only snapshot of the three authored strategy/validation drafts."""

from typing import Protocol
from product_strategy_agent.domain.projects.numeric_inventory import (
    NumericInventorySnapshot,
)


class NumericInventoryReader(Protocol):
    def read(self, project_id: str) -> NumericInventorySnapshot: ...
