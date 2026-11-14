"""Compose bounded draft readers under one common case lock; no evidence acquisition."""

from product_strategy_agent.adapters.persistence.files.strategy_structure_reader import (
    FileStrategyStructureReader,
)
from product_strategy_agent.adapters.persistence.files.validation_plan_store import (
    FileValidationPlanStore,
)
from product_strategy_agent.domain.projects.numeric_inventory import (
    NumericInventorySnapshot,
)


class FileNumericInventoryReader:
    def __init__(self, root):
        self.strategy = FileStrategyStructureReader(root)
        self.validation = FileValidationPlanStore(root)

    def read(self, project_id):
        with self.validation.access(project_id):
            strategy = self.strategy.read(project_id)
            validation = self.validation.read(project_id)
            if (
                strategy.version != validation.version
                or strategy.input_hashes["state.json"]
                != validation.input_hashes["state.json"]
            ):
                raise ValueError("numeric inventory inputs changed during read")
            return NumericInventorySnapshot(
                strategy.version,
                {
                    **strategy.documents,
                    "drafts/validation-plan.md": validation.markdown,
                },
                {**strategy.input_hashes, **validation.input_hashes},
            )
