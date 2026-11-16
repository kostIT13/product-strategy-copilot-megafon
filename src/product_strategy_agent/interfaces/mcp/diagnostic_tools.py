"""Read-only historical metadata without case material, role text or actor/reason fields."""

from uuid import UUID
from product_strategy_agent.domain.automation.operation_diagnostics import (
    DiagnoseOperation,
    OperationKind,
)
from product_strategy_agent.interfaces.operation_diagnostics import (
    operation_diagnostics,
)


def register_diagnostic_tools(server):
    from fastmcp.exceptions import ToolError

    @server.tool(
        annotations=dict(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        )
    )
    def psa_diagnose_operation(
        project_id: str,
        operation_id: UUID,
        kind: OperationKind,
        projects_dir: str = "projects",
    ) -> dict:
        """Inspect one task/result/review/hook journal operation; never run, retry or recover.

        Captured snapshot is historical; freshness is not checked. Usage is self-reported with
        unknown measurement basis, missing usage remains null. Pending outcomes are unpublished.
        No source/role/finding/reason/actor text returned, no gate approval or native activation.
        """
        try:
            return operation_diagnostics(projects_dir).inspect(
                DiagnoseOperation(
                    project_id=project_id, operation_id=operation_id, kind=kind
                )
            )
        except (ValueError, OSError):
            raise ToolError(
                "operation diagnostic unavailable; inspect case lock, namespace and journal integrity"
            ) from None
