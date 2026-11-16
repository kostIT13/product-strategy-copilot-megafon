"""Read one bound operation without exposing its request, material or diagnostic text."""

from typing import Protocol
from product_strategy_agent.domain.automation.operation_diagnostics import (
    DiagnoseOperation,
    OperationFacts,
)


class OperationDiagnosticsReader(Protocol):
    def read(self, request: DiagnoseOperation) -> OperationFacts | None: ...
