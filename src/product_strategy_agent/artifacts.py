"""Read integrity and journal adoption of existing generated documents."""
from pathlib import Path
from uuid import uuid4
from product_strategy_agent.adapters.persistence.files.case_access import locked_case
from product_strategy_agent.adapters.persistence.files.paths import confined
from product_strategy_agent.adapters.persistence.files.artifact_bundle import read_small
from product_strategy_agent.adapters.persistence.files.workflow_repository import FileWorkflowStore
from product_strategy_agent.application.services.render_service import RenderService
from product_strategy_agent.domain.projects.render_plan import (
    GENERATED_ARTIFACTS, MANIFEST_NAME, RenderRequest, integrity_report, parse_manifest)


def _text(project_dir, name):
    path = confined(Path(project_dir).absolute(), name)
    return read_small(path.parent, path.name).decode("utf-8") if path.exists() else None


def _read_manifest(project_dir):
    return parse_manifest(_text(project_dir, MANIFEST_NAME))


@locked_case
def render_integrity_report(project_dir: Path) -> dict:
    return integrity_report({name: _text(project_dir, name) for name in (*GENERATED_ARTIFACTS, MANIFEST_NAME)})


@locked_case
def adopt_existing_render(project_dir: Path, *, operation_id=None, expected_workflow_version=None) -> dict:
    project_dir = Path(project_dir).absolute()
    command = RenderRequest(operation_id=uuid4() if operation_id is None else operation_id, mode="adopt",
                            expected_workflow_version=expected_workflow_version)
    result = RenderService(FileWorkflowStore(project_dir.parent)).run(project_dir.name, command)
    return {**result, "manifest": str(project_dir / result["manifest"])}


@locked_case
def write_render_manifest(project_dir: Path, *, adopted_existing: bool = False,
                          operation_id=None, expected_workflow_version=None) -> Path:
    """Compatibility tracking helper: journal adoption, never claim regeneration."""
    return Path(adopt_existing_render(project_dir, operation_id=operation_id,
                                      expected_workflow_version=expected_workflow_version)["manifest"])
