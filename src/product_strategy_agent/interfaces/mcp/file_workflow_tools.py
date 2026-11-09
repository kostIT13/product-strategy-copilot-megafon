"""Thin recovery tools; bypass pending-case entry guard only for explicit recovery."""
from uuid import UUID
from product_strategy_agent.application.services.workflow_recovery_service import WorkflowRecoveryService
from product_strategy_agent.adapters.persistence.files.workflow_repository import FileWorkflowStore


def register_file_workflow_tools(server):
    from fastmcp.exceptions import ToolError

    def invoke(action, project_id, projects_dir, operation_id=None):
        service = WorkflowRecoveryService(FileWorkflowStore(projects_dir))
        try:
            if action == "recover":
                return service.recover(project_id, operation_id)
            return service.pending(project_id)
        except ValueError as error:
            raise ToolError(str(error)) from None
        except OSError:
            raise ToolError("workflow files unavailable; preserve preparations and inspect the case") from None

    @server.tool(annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False})
    def psa_pending_workflow(project_id: str, projects_dir: str = "projects") -> dict:
        """Inspect interrupted workflow publication; never infer approval or repair data."""
        return invoke("pending", project_id, projects_dir)

    @server.tool(annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False})
    def psa_recover_workflow(project_id: str, operation_id: UUID, projects_dir: str = "projects") -> dict:
        """Finish the exact already-authorized workflow operation; reject changed files/inputs."""
        return invoke("recover", project_id, projects_dir, operation_id)
