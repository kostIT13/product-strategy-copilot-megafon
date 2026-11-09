"""Publish readable artifacts through the shared recoverable workflow journal."""
from pathlib import Path
from uuid import uuid4
from product_strategy_agent.adapters.persistence.files.case_access import locked_case
from product_strategy_agent.adapters.persistence.files.workflow_repository import FileWorkflowStore
from product_strategy_agent.application.services.render_service import RenderService
from product_strategy_agent.domain.projects.render_plan import RenderRequest
from product_strategy_agent.domain.projects.render_templates import DRAFTS


@locked_case
def render_project(project_dir: Path, *, discard_generated_edits_by: str = "", discard_reason: str = "",
                   operation_id=None, expected_workflow_version=None) -> list[Path]:
    project_dir = Path(project_dir).absolute()
    command = RenderRequest(operation_id=uuid4() if operation_id is None else operation_id,
        discard_by=discard_generated_edits_by, reason=discard_reason, expected_workflow_version=expected_workflow_version)
    result = RenderService(FileWorkflowStore(project_dir.parent)).run(project_dir.name, command)
    return [project_dir / name for name in result["rendered"]]
