"""Read-only historical metadata without case material, role text or actor/reason fields."""

from uuid import UUID
import json
from product_strategy_agent.interfaces.usage_provenance import usage_provenance
from product_strategy_agent.domain.automation.operation_summary import parse_summary
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
    def psa_operation_controls(
        project_id: str,
        operation_id: UUID,
        kind: OperationKind,
        projects_dir: str = "projects",
    ) -> dict:
        """Read advisory retry/replay/recovery capabilities for one journal operation.

        No execution, cancellation, checkpoint resume or authorization evaluation. Native
        host controls stay not_verified; recorded cancelled/passed is not capability proof.
        Freshness and active writer/permissions must be checked at the separate real action.
        """
        try:
            return operation_diagnostics(projects_dir).controls(
                DiagnoseOperation(
                    project_id=project_id, operation_id=operation_id, kind=kind
                )
            )
        except (ValueError, OSError):
            raise ToolError(
                "operation controls unavailable; inspect case lock, namespace and journal integrity"
            ) from None

    @server.tool(
        annotations=dict(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        )
    )
    def psa_diagnose_usage(project_id: str, projects_dir: str = "projects") -> dict:
        """Read bounded v1 usage declarations with file/row hashes and redacted provenance.

        Measured/estimated cost is a recorded declaration, not independent verification.
        Missing metrics stay null; no totals, provider/model/note text or inferred binding to
        automation operations. Never writes records, calls a model or approves a gate.
        """
        try:
            return usage_provenance(projects_dir).inspect(project_id)
        except (ValueError, OSError):
            raise ToolError(
                "usage provenance unavailable; inspect case lock and bounded ledger integrity"
            ) from None

    @server.tool(
        annotations=dict(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        )
    )
    def psa_summarize_operations(request: dict, projects_dir: str = "projects") -> dict:
        """Summarize 1-32 explicitly selected operations in one case under one shared lock.

        Selection is not the whole case. Pending outcomes stay unpublished; no usage totals or
        inferred running/cancel status. Fixed read-only guidance is data, never permission to
        recover, retry, dispatch or approve. Add the caller's --projects-dir to inspection argv.
        """
        try:
            parsed = parse_summary(
                json.dumps(request, ensure_ascii=False, allow_nan=False).encode("utf-8")
            )
            return operation_diagnostics(projects_dir).summary(parsed)
        except (ValueError, OSError):
            raise ToolError(
                "operation summary unavailable; inspect selection, case lock, namespace and journal integrity"
            ) from None

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
