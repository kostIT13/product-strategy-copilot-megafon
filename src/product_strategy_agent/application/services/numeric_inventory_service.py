"""Discover digit tokens without assessing claims, performing math or changing files."""

from product_strategy_agent.application.ports.numeric_inventory_reader import (
    NumericInventoryReader,
)
from product_strategy_agent.domain.projects.numeric_inventory import inventory_report
from product_strategy_agent.domain.projects.workspace import validate_workspace_id


class NumericInventoryService:
    def __init__(self, reader: NumericInventoryReader):
        self.reader = reader

    def inspect(self, project_id):
        validate_workspace_id(project_id)
        return inventory_report(project_id, self.reader.read(project_id))
