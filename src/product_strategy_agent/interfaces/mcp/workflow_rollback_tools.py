"""Explicit human-requested rollback through the same application service as CLI."""

from uuid import UUID, uuid4
from pydantic import ValidationError
from product_strategy_agent.adapters.persistence.files.workflow_repository import (
    FileWorkflowStore,
)
from product_strategy_agent.application.services.workflow_rollback_service import (
    WorkflowRollbackService,
)
from product_strategy_agent.domain.projects.workflow_reopen import ReopenStage
from product_strategy_agent.domain.projects.workflow_rollback import WorkflowRollback


def register_workflow_rollback_tools(server):
    from fastmcp.exceptions import ToolError

    @server.tool(
        annotations={
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": False,
            "openWorldHint": False,
        }
    )
    def psa_rollback_workflow(
        project_id: str,
        target_stage: ReopenStage,
        rolled_back_by: str,
        reason: str,
        review_hash: str,
        expected_workflow_version: int,
        projects_dir: str = "projects",
        operation_id: UUID | None = None,
    ) -> dict:
        """Only on explicit human instruction: return active work to a strictly earlier stage.

        Requires the current workflow review hash/version. Preserves evidence/choices/old approvals,
        invalidates selected and later stages; repeated gates, fresh decision/reviews/render apply.
        Caller UUID supports exact historical replay and explicit recovery after interruption.
        """
        try:
            return WorkflowRollbackService(FileWorkflowStore(projects_dir)).rollback(
                project_id,
                WorkflowRollback(
                    operation_id=operation_id or uuid4(),
                    target_stage=target_stage,
                    rolled_back_by=rolled_back_by,
                    reason=reason,
                    review_hash=review_hash,
                    expected_workflow_version=expected_workflow_version,
                ),
            )
        except ValidationError:
            raise ToolError("invalid workflow rollback fields") from None
        except ValueError as error:
            raise ToolError(str(error)) from None
        except OSError:
            raise ToolError(
                "workflow files unavailable; inspect pending before retrying"
            ) from None
