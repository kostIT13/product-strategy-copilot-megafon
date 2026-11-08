"""Preview or start a linked critic pipeline for an existing draft run."""
from dataclasses import asdict
import json
from uuid import UUID
from product_strategy_agent.bootstrap import build_main_services
from product_strategy_agent.domain.projects.errors import ProjectNotFound
from product_strategy_agent.interfaces.payloads import analysis_preview, json_payload


def add_critic_commands(commands):
    parser = commands.add_parser("critic", help="Assess a saved draft against its pinned evidence")
    actions = parser.add_subparsers(dest="action", required=True)
    for name in ("prepare", "start"):
        command = actions.add_parser(name)
        command.add_argument("project_key")
        command.add_argument("run_id", type=UUID)


def handle_critic_command(args):
    try:
        service = build_main_services().critic
        if args.action == "prepare":
            result = analysis_preview(service.prepare(args.project_key, args.run_id))
        else:
            result = json_payload(asdict(service.start(args.project_key, args.run_id)))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, ProjectNotFound) as exc:
        print(f"Error: {exc}")
        return 2
