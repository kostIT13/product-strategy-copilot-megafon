"""Thin recovery tools; bypass pending-case entry guard only for explicit recovery."""

from uuid import UUID, uuid4
from pydantic import ValidationError
from product_strategy_agent.application.services.workflow_reopen_service import (
    WorkflowReopenService,
)
from product_strategy_agent.domain.projects.workflow_reopen import (
    WorkflowReopen,
    ReopenStage,
)
from product_strategy_agent.application.services.workflow_recovery_service import (
    WorkflowRecoveryService,
)
from product_strategy_agent.adapters.persistence.files.workflow_repository import (
    FileWorkflowStore,
)


def register_file_workflow_tools(server):
    from fastmcp.exceptions import ToolError

    @server.tool(
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        }
    )
    def psa_review_workflow(project_id: str, projects_dir: str = "projects") -> dict:
        """Read current workflow/evidence impact and snapshot hash; grants no permission."""
        try:
            return WorkflowReopenService(FileWorkflowStore(projects_dir)).review(
                project_id
            )
        except (ValueError, OSError):
            raise ToolError(
                "workflow review unavailable; inspect case integrity and pending operations"
            ) from None

    @server.tool(
        annotations={
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": False,
            "openWorldHint": False,
        }
    )
    def psa_reopen_workflow(
        project_id: str,
        target_stage: ReopenStage,
        reopened_by: str,
        reason: str,
        review_hash: str,
        expected_workflow_version: int,
        projects_dir: str = "projects",
        operation_id: UUID | None = None,
    ) -> dict:
        """Only on explicit human instruction: reopen completed workflow at selected stage.

        Requires workflow review snapshot; preserves historical approvals and human choices.
        Selected and later stages require new gates. Caller UUID supports exact replay/recovery.
        """
        try:
            command = WorkflowReopen(
                operation_id=operation_id or uuid4(),
                target_stage=target_stage,
                reopened_by=reopened_by,
                reason=reason,
                review_hash=review_hash,
                expected_workflow_version=expected_workflow_version,
            )
            return WorkflowReopenService(FileWorkflowStore(projects_dir)).reopen(
                project_id, command
            )
        except ValidationError:
            raise ToolError("invalid workflow reopen fields") from None
        except ValueError as error:
            raise ToolError(str(error)) from None
        except OSError:
            raise ToolError(
                "workflow files unavailable; inspect pending before retrying"
            ) from None

    def invoke(action, project_id, projects_dir, operation_id=None):
        service = WorkflowRecoveryService(FileWorkflowStore(projects_dir))
        try:
            if action == "recover":
                return service.recover(project_id, operation_id)
            return service.pending(project_id)
        except ValueError as error:
            raise ToolError(str(error)) from None
        except OSError:
            raise ToolError(
                "workflow files unavailable; preserve preparations and inspect the case"
            ) from None

    @server.tool(
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        }
    )
    def psa_pending_workflow(project_id: str, projects_dir: str = "projects") -> dict:
        """Inspect interrupted workflow publication; never infer approval or repair data."""
        return invoke("pending", project_id, projects_dir)

    @server.tool(
        annotations={
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        }
    )
    def psa_recover_workflow(
        project_id: str, operation_id: UUID, projects_dir: str = "projects"
    ) -> dict:
        """Finish the exact already-authorized workflow operation; reject changed files/inputs."""
        return invoke("recover", project_id, projects_dir, operation_id)
