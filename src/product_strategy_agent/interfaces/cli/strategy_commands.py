"""Decision-bound strategy drafting via the common checkpoint pipeline."""
from dataclasses import asdict
import json
from uuid import UUID
from product_strategy_agent.bootstrap import build_main_services
from product_strategy_agent.domain.projects.errors import ProjectNotFound
from product_strategy_agent.interfaces.payloads import analysis_preview, json_payload


def add_strategy_commands(commands):
    parser = commands.add_parser("strategy", help="Draft product, communication and experiment plans for a recorded selection")
    actions = parser.add_subparsers(dest="action", required=True)
    for name in ("prepare", "start"):
        command = actions.add_parser(name)
        command.add_argument("project_key")
        command.add_argument("source_run_id", type=UUID, help="Options run with a recorded human selection")
        command.add_argument("--question", required=True)


def handle_strategy_command(args):
    try:
        service = build_main_services().strategy
        if args.action == "prepare":
            result = analysis_preview(service.prepare(args.project_key, args.source_run_id, args.question))
        else:
            result = json_payload(asdict(service.start(args.project_key, args.source_run_id, args.question)))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, ProjectNotFound) as exc:
        print(f"Error: {exc}" if type(exc) is ValueError or isinstance(exc, ProjectNotFound) else "Error: invalid strategy context")
        return 2
