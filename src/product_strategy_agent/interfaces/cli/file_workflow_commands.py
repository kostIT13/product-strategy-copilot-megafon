"""Inspect and recover gate state/events publication without reissuing consent."""
import json
from pathlib import Path
from uuid import UUID
from product_strategy_agent.application.services.workflow_recovery_service import WorkflowRecoveryService
from product_strategy_agent.adapters.persistence.files.workflow_repository import FileWorkflowStore


def add_workflow_commands(commands):
    parser = commands.add_parser("workflow", help="Inspect/recover interrupted workflow approvals")
    actions = parser.add_subparsers(dest="workflow_action", required=True)
    for name in ("pending", "recover"):
        action = actions.add_parser(name)
        action.add_argument("project_id")
        action.add_argument("--projects-dir", type=Path, default=Path("projects"))
        if name == "recover":
            action.add_argument("--operation", type=UUID, required=True)


def handle_workflow_command(args):
    service = WorkflowRecoveryService(FileWorkflowStore(args.projects_dir))
    if args.workflow_action == "recover":
        result = service.recover(args.project_id, args.operation)
    else:
        result = service.pending(args.project_id)
    print(json.dumps(result, ensure_ascii=True, indent=2))
