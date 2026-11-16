"""Composition shared by CLI/FastMCP; no execution or recovery services."""

from product_strategy_agent.adapters.persistence.files.operation_diagnostics_reader import (
    FileOperationDiagnosticsReader,
)
from product_strategy_agent.application.services.operation_diagnostics_service import (
    OperationDiagnosticsService,
)


def operation_diagnostics(projects_dir):
    return OperationDiagnosticsService(FileOperationDiagnosticsReader(projects_dir))
