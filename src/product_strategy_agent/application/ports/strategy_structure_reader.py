"""Read-only coherent author-draft snapshot."""

from typing import Protocol
from product_strategy_agent.domain.projects.strategy_structure import StrategySnapshot


class StrategyStructureReader(Protocol):
    def read(self, project_id: str) -> StrategySnapshot: ...
