"""Thin CLI for inspecting/recovering prepared initialization operations."""
import json
from pathlib import Path
from uuid import UUID
from product_strategy_agent.application.services.workspace_service import WorkspaceService
from product_strategy_agent.adapters.persistence.files.workspace_repository import FileWorkspaceStore


def add_workspace_commands(commands):
    workspace = commands.add_parser("workspace", help="Inspect/recover interrupted initialization")
    actions = workspace.add_subparsers(dest="workspace_action", required=True)
    for name in ("pending", "recover"):
        parser = actions.add_parser(name)
        parser.add_argument("project_id")
        parser.add_argument("--projects-dir", type=Path, default=Path("projects"))
        if name == "recover":
            parser.add_argument("--operation", type=UUID, required=True)


def handle_workspace_command(args):
    service = WorkspaceService(FileWorkspaceStore(args.projects_dir))
    if args.workspace_action == "pending":
        payload = {"project_id": args.project_id, "preparations": service.pending(args.project_id), "read_only": True}
    else:
        path = service.recover(args.project_id, args.operation)
        payload = {"project_id": args.project_id, "operation_id": str(args.operation), "path": str(path), "status": "committed"}
    print(json.dumps(payload, ensure_ascii=True, indent=2))
