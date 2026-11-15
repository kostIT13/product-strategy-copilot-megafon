"""Subagent preparation and isolated records; no dispatch or canonical adoption."""

import json
from pathlib import Path
from uuid import UUID
from product_strategy_agent.domain.automation.handoffs import parse_request
from product_strategy_agent.domain.automation.task_records import (
    parse_result_request,
    parse_review_request,
)
from product_strategy_agent.interfaces.subagent_journal import journal_service


def add_subagent_commands(commands):
    parser = commands.add_parser(
        "subagent", help="prepare handoffs and isolated task records; no execution"
    )
    actions = parser.add_subparsers(dest="subagent_action", required=True)
    for name in (
        "prepare",
        "register",
        "record-result",
        "review-result",
        "task",
        "result",
        "review",
        "pending",
        "recover",
    ):
        action = actions.add_parser(name)
        action.add_argument("project_id")
        action.add_argument("--projects-dir", type=Path, default=Path("projects"))
        action.add_argument("--instructions-root", type=Path, default=Path("."))
        if name in ("prepare", "register", "record-result", "review-result"):
            action.add_argument("--request", type=Path, required=True)
        if name == "register":
            action.add_argument("--by", required=True)
        if name == "task":
            action.add_argument("--task", type=UUID, required=True)
        if name in ("result", "review"):
            action.add_argument("--operation", type=UUID, required=True)
        if name == "recover":
            action.add_argument(
                "--kind", choices=("task", "result", "review"), required=True
            )
            action.add_argument("--id", type=UUID, required=True)


def handle_subagent_command(args):
    name = args.subagent_action
    app = journal_service(args.projects_dir, args.instructions_root)
    if name in ("prepare", "register", "record-result", "review-result"):
        limit = 64000 if name in ("prepare", "register") else 128000
        with args.request.open("rb") as stream:
            raw = stream.read(limit + 1)
        if len(raw) > limit:
            raise ValueError(f"subagent request exceeds {limit} bytes")
        if name == "prepare":
            result = app.handoffs.prepare(args.project_id, parse_request(raw))
        elif name == "register":
            result = app.register(args.project_id, parse_request(raw), args.by)
        elif name == "record-result":
            result = app.record_result(args.project_id, parse_result_request(raw))
        else:
            result = app.review_result(args.project_id, parse_review_request(raw))
    elif name == "task":
        result = app.show_task(args.project_id, args.task)
    elif name == "result":
        result = app.show_result(args.project_id, args.operation)
    elif name == "review":
        result = app.show_review(args.project_id, args.operation)
    elif name == "pending":
        result = app.pending(args.project_id)
    else:
        result = app.recover(args.project_id, args.kind, args.id)
    print(json.dumps(result, ensure_ascii=True, indent=2))
