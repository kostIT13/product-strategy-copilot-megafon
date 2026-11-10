"""Withdrawal requires explicit human instruction; never rewrite a decision."""

from uuid import UUID, uuid4
from product_strategy_agent.adapters.persistence.files.workflow_repository import (
    FileWorkflowStore,
)
from product_strategy_agent.application.services.claim_lifecycle_service import (
    ClaimLifecycleService,
)
from product_strategy_agent.domain.projects.claim_lifecycle import ClaimWithdrawal


def register_claim_lifecycle_tools(server):
    from fastmcp.exceptions import ToolError

    def invoke(project_id, projects_dir, command=None):
        service = ClaimLifecycleService(FileWorkflowStore(projects_dir))
        try:
            return (
                service.withdraw(project_id, command)
                if command is not None
                else service.impact(project_id)
            )
        except ValueError as error:
            raise ToolError(str(error)) from None
        except OSError:
            raise ToolError(
                "claim lifecycle files unavailable; inspect pending workflow before retrying"
            ) from None

    @server.tool(
        annotations={
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": False,
            "openWorldHint": False,
        }
    )
    def psa_withdraw_claim(
        project_id: str,
        claim_id: str,
        withdrawn_by: str,
        reason: str,
        projects_dir: str = "projects",
        operation_id: UUID | None = None,
        expected_workflow_version: int | None = None,
    ) -> dict:
        """Explicit human-authorized claim withdrawal. Original record and decisions stay in history.

        Caller UUID enables exact replay; recovery uses the shared workflow pending/recover tools.
        Supplying a name is self-reported attribution, not authentication or inferred consent.
        """
        command = ClaimWithdrawal(
            operation_id=operation_id or uuid4(),
            claim_id=claim_id,
            withdrawn_by=withdrawn_by,
            reason=reason,
            expected_workflow_version=expected_workflow_version,
        )
        return invoke(project_id, projects_dir, command)

    @server.tool(
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        }
    )
    def psa_claim_impact(project_id: str, projects_dir: str = "projects") -> dict:
        """Read effective statuses and dependent options/capabilities/decisions needing review; never approve changes."""
        return invoke(project_id, projects_dir)
