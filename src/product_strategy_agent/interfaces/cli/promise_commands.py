"""Check IDE-authored promises against canonical evidence, with no writes/model call."""
import json
from pathlib import Path
from product_strategy_agent.bootstrap import build_promise_service
from product_strategy_agent.domain.capabilities.promises import PromiseCheckRequest
from product_strategy_agent.domain.projects.errors import ProjectNotFound


def add_promise_commands(commands):
    parser = commands.add_parser("promise", help="Read-only capability/evidence preflight for promise candidates")
    actions = parser.add_subparsers(dest="action", required=True)
    check = actions.add_parser("check")
    check.add_argument("project_key")
    check.add_argument("--input", type=Path, required=True, help="JSON PromiseCheckRequest authored by an IDE agent or human")


def handle_promise_command(args):
    try:
        if args.input.stat().st_size > 64000:
            raise ValueError("promise input exceeds the 64000-byte limit")
        request = PromiseCheckRequest.model_validate_json(args.input.read_text(encoding="utf-8"))
        result = build_promise_service().check(args.project_key, request)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 3 if result["structural_status"] == "blocked" else 0
    except (ValueError, OSError, ProjectNotFound) as exc:
        print(f"Error: {exc}" if type(exc) is ValueError or isinstance(exc, ProjectNotFound) else "Error: invalid promise check input")
        return 2
