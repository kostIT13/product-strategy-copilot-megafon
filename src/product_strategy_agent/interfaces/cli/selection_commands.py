"""Preview and explicitly record a human choice from reviewed model alternatives."""
import json
from pathlib import Path
from uuid import UUID
from product_strategy_agent.bootstrap import build_main_services
from product_strategy_agent.domain.decisions.selection import SelectionCommand
from product_strategy_agent.domain.projects.errors import ProjectNotFound


def add_selection_commands(commands):
    parser = commands.add_parser("selection", help="Record an explicit human choice of reviewed AI alternatives")
    actions = parser.add_subparsers(dest="action", required=True)
    preview = actions.add_parser("preview")
    preview.add_argument("project_key")
    preview.add_argument("source_run_id", type=UUID)
    preview.add_argument("critic_run_id", type=UUID)
    show = actions.add_parser("show")
    show.add_argument("project_key")
    show.add_argument("source_run_id", type=UUID)
    record = actions.add_parser("record")
    record.add_argument("project_key")
    record.add_argument("--input", type=Path, required=True, help="JSON SelectionCommand with explicit human confirmation")


def handle_selection_command(args):
    try:
        service = build_main_services().selection
        if args.action == "preview":
            result = service.preview(args.project_key, args.source_run_id, args.critic_run_id)
        elif args.action == "show":
            result = service.get(args.project_key, args.source_run_id)
        else:
            command = SelectionCommand.model_validate_json(args.input.read_text(encoding="utf-8"))
            result = service.record(args.project_key, command)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, ProjectNotFound) as exc:
        # Pydantic errors can contain submitted text: emit only the error category.
        print(f"Error: {exc}" if type(exc) is ValueError or isinstance(exc, ProjectNotFound) else "Error: invalid selection input")
        return 2
