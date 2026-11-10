"""Structural completeness of strategy drafts without model calls or approval."""

from product_strategy_agent.application.ports.strategy_structure_reader import (
    StrategyStructureReader,
)
from product_strategy_agent.domain.projects.strategy_structure import structure_report
from product_strategy_agent.domain.projects.workspace import validate_workspace_id


class StrategyStructureService:
    def __init__(self, reader: StrategyStructureReader):
        self.reader = reader

    def check(self, project_id: str) -> dict:
        validate_workspace_id(project_id)
        return structure_report(project_id, self.reader.read(project_id))
