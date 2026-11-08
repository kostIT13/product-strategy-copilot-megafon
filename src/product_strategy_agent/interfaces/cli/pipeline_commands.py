"""Explicit versioned checkpoint operations for the draft agent pipeline."""
import json
from dataclasses import asdict
from uuid import UUID
from product_strategy_agent.bootstrap import build_main_services
from product_strategy_agent.domain.projects.errors import ProjectNotFound
from product_strategy_agent.interfaces.payloads import json_payload


def add_pipeline_commands(commands):
    parser = commands.add_parser("pipeline", help="Checkpointed evidence/draft/review execution")
    actions = parser.add_subparsers(dest="action", required=True)
    start = actions.add_parser("start", help="Pin evidence without calling the model")
    start.add_argument("project_key")
    start.add_argument("--question", required=True)
    start.add_argument("--query", required=True)
    for name in ("show", "resume"):
        command = actions.add_parser(name)
        command.add_argument("project_key")
        command.add_argument("pipeline_id", type=UUID)
        if name == "resume":
            command.add_argument("--expected-version", type=int, required=True)


def handle_pipeline_command(args):
    try:
        service = build_main_services().pipeline
        if args.action == "start":
            pipeline = service.start(args.project_key, args.question, args.query)
        elif args.action == "show":
            pipeline = service.show(args.project_key, args.pipeline_id)
        else:
            pipeline = service.resume(args.project_key, args.pipeline_id, args.expected_version)
        print(json.dumps(json_payload(asdict(pipeline)), ensure_ascii=False, indent=2))
        return 2 if pipeline.status == "failed" else 0
    except (ValueError, ProjectNotFound) as exc:
        print(f"Error: {exc}")
        return 2
