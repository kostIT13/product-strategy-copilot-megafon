"""Human-instructed source withdrawal; no deletion, replacement or inferred choice."""

from uuid import UUID, uuid4
from pydantic import ValidationError
from product_strategy_agent.adapters.persistence.files.workflow_repository import (
    FileWorkflowStore,
)
from product_strategy_agent.application.services.source_lifecycle_service import (
    SourceLifecycleService,
)
from product_strategy_agent.domain.projects.source_lifecycle import SourceWithdrawal


def register_source_lifecycle_tools(server):
    from fastmcp.exceptions import ToolError

    @server.tool(
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        }
    )
    def psa_source_impact(project_id: str, projects_dir: str = "projects") -> dict:
        """Read withdrawn sources, dependent claims/options/capabilities/decisions; never approve changes."""
        try:
            return SourceLifecycleService(FileWorkflowStore(projects_dir)).impact(
                project_id
            )
        except (ValueError, OSError):
            raise ToolError(
                "source impact unavailable; inspect case integrity and pending operations"
            ) from None

    @server.tool(
        annotations={
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": False,
            "openWorldHint": False,
        }
    )
    def psa_withdraw_source(
        project_id: str,
        source_id: str,
        withdrawn_by: str,
        reason: str,
        projects_dir: str = "projects",
        operation_id: UUID | None = None,
        expected_workflow_version: int | None = None,
    ) -> dict:
        """Withdraw only on explicit human instruction; preserve registry/text and decision history.

        References become inactive; reimport cannot restore eligibility. UUID replays without acquisition.
        Use workflow pending/recover for interruptions. Attribution is not authentication.
        """
        try:
            command = SourceWithdrawal(
                operation_id=operation_id or uuid4(),
                source_id=source_id,
                withdrawn_by=withdrawn_by,
                reason=reason,
                expected_workflow_version=expected_workflow_version,
            )
            return SourceLifecycleService(FileWorkflowStore(projects_dir)).withdraw(
                project_id, command
            )
        except ValidationError:
            raise ToolError("invalid source withdrawal fields") from None
        except ValueError as error:
            raise ToolError(str(error)) from None
        except OSError:
            raise ToolError(
                "source lifecycle files unavailable; inspect pending before retrying"
            ) from None
