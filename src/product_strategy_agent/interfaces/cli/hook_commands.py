"""Explicit read-only before-gate preflight, without activation or approvals."""

import json
from pathlib import Path
from uuid import UUID
from product_strategy_agent.interfaces.hook_preflight import (
    hook_preflight,
    parse_hook_request,
)
from product_strategy_agent.application.services.hook_preflight_service import TRIGGERS


def add_hook_commands(commands):
    parser = commands.add_parser(
        "hook", help="explicit local preflight; no approval or activation"
    )
    actions = parser.add_subparsers(dest="hook_action", required=True)
    prepare = actions.add_parser("prepare")
    prepare.add_argument("project_id")
    prepare.add_argument("--trigger", choices=tuple(TRIGGERS), required=True)
    prepare.add_argument("--operation", type=UUID, required=True)
    check = actions.add_parser("check")
    check.add_argument("--request", type=Path, required=True)
    for action in (prepare, check):
        action.add_argument("--projects-dir", type=Path, default=Path("projects"))


def handle_hook_command(args):
    app = hook_preflight(args.projects_dir)
    if args.hook_action == "prepare":
        result = app.prepare(args.project_id, args.trigger, args.operation)
    else:
        with args.request.open("rb") as stream:
            command = parse_hook_request(stream.read(64001))
        result = app.check(command)
    print(json.dumps(result, ensure_ascii=True, indent=2))
    if args.hook_action == "check" and result["status"] != "passed":
        raise SystemExit(1)
