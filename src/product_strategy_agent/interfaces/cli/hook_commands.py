"""Explicit preflight/source notices and journal lifecycle, without activation or approval."""

import json
from pathlib import Path
from uuid import UUID
from product_strategy_agent.interfaces.hook_preflight import (
    hook_preflight,
    parse_hook_request,
)
from product_strategy_agent.application.services.hook_preflight_service import TRIGGERS
from product_strategy_agent.interfaces.hook_runs import hook_runs, hook_run_command
from product_strategy_agent.interfaces.source_notification import source_notification


def add_hook_commands(commands):
    parser = commands.add_parser(
        "hook", help="explicit local preflight; no approval or activation"
    )
    actions = parser.add_subparsers(dest="hook_action", required=True)
    prepare = actions.add_parser("prepare")
    prepare.add_argument("project_id")
    prepare.add_argument("--trigger", choices=tuple(TRIGGERS), required=True)
    prepare.add_argument("--operation", type=UUID, required=True)
    notification = actions.add_parser("prepare-notification")
    notification.add_argument("project_id")
    notification.add_argument("--operation", type=UUID, required=True)
    check = actions.add_parser("check")
    check.add_argument("--request", type=Path, required=True)
    run = actions.add_parser("run")
    run.add_argument("--request", type=Path, required=True)
    run.add_argument("--timeout", type=int, default=30)
    inspections = []
    for name in ("show", "pending", "recover"):
        action = actions.add_parser(name)
        action.add_argument("project_id")
        if name != "pending":
            action.add_argument("--operation", type=UUID, required=True)
        inspections.append(action)
    for action in (prepare, notification, check, run, *inspections):
        action.add_argument("--projects-dir", type=Path, default=Path("projects"))


def handle_hook_command(args):
    app = hook_preflight(args.projects_dir)
    if args.hook_action == "prepare":
        result = app.prepare(args.project_id, args.trigger, args.operation)
    elif args.hook_action == "prepare-notification":
        result = source_notification(args.projects_dir).prepare(
            args.project_id, args.operation
        )
    elif args.hook_action in ("check", "run"):
        with args.request.open("rb") as stream:
            command = parse_hook_request(stream.read(64001))
        if args.hook_action == "check":
            result = app.check(command)
        else:
            result = hook_runs(args.projects_dir).run(
                hook_run_command(command, args.timeout)
            )
    else:
        service = hook_runs(args.projects_dir)
        if args.hook_action == "pending":
            result = service.pending(args.project_id)
        elif args.hook_action == "show":
            result = service.show(args.project_id, args.operation)
        else:
            result = service.recover(args.project_id, args.operation)
    print(json.dumps(result, ensure_ascii=True, indent=2))
    if args.hook_action == "check" and result["status"] != "passed":
        raise SystemExit(1)
    if args.hook_action == "run" and not (
        result["required_check_passed"] or result["notification_delivered"]
    ):
        raise SystemExit(1)
