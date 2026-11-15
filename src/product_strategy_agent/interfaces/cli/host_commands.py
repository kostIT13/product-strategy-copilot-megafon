"""Read-only host inspection and plan; does not alter IDE configurations."""

import json
from product_strategy_agent.interfaces.cli.host_review_commands import (
    add_review_actions,
    handle_review_command,
)
from pathlib import Path
from product_strategy_agent.interfaces.host_profiles import (
    host_profiles,
    parse_host_plan,
)
from uuid import UUID
from product_strategy_agent.interfaces.host_acceptance import (
    host_acceptance,
    evidence_reader,
)
from product_strategy_agent.domain.automation.host_acceptance import (
    parse_record_request,
)


def add_host_commands(commands):
    parser = commands.add_parser(
        "host", help="inspect unverified host profiles and plan sequential fallback"
    )
    actions = parser.add_subparsers(dest="host_action", required=True)
    for name in ("list", "inspect", "plan"):
        action = actions.add_parser(name)
        action.add_argument("--instructions-root", type=Path, default=Path("."))
        if name == "inspect":
            action.add_argument("host_id")
        if name == "plan":
            action.add_argument("--request", type=Path, required=True)
    for name in (
        "acceptance-prepare",
        "acceptance-record",
        "acceptance-show",
        "acceptance-pending",
        "acceptance-recover",
    ):
        action = actions.add_parser(name)
        action.add_argument("--instructions-root", type=Path, default=Path("."))
        if name in ("acceptance-prepare", "acceptance-record"):
            action.add_argument("--request", type=Path, required=True)
        if name in ("acceptance-prepare", "acceptance-show", "acceptance-recover"):
            action.add_argument("--operation", type=UUID, required=True)
        if name == "acceptance-record":
            action.add_argument("--evidence-dir", type=Path, required=True)
    add_review_actions(actions)


def handle_host_command(args):
    if args.host_action.startswith("review-") or args.host_action == "preview-codex":
        return handle_review_command(args)
    if args.host_action.startswith("acceptance-"):
        return handle_acceptance(args)
    service = host_profiles(args.instructions_root)
    if args.host_action == "list":
        result = service.catalog()
    elif args.host_action == "inspect":
        result = service.profile(args.host_id)
    else:
        with args.request.open("rb") as stream:
            command = parse_host_plan(stream.read(64001))
        result = service.plan(command)
    print(json.dumps(result, ensure_ascii=True, indent=2))
    if args.host_action == "plan" and result["status"] == "fallback_required":
        raise SystemExit(1)


def handle_acceptance(args):
    service = host_acceptance(args.instructions_root)
    name = args.host_action
    if name in ("acceptance-prepare", "acceptance-record"):
        with args.request.open("rb") as stream:
            raw = stream.read(64001)
        if name == "acceptance-prepare":
            result = service.prepare(parse_host_plan(raw), args.operation)
        else:
            result = service.record(
                parse_record_request(raw), evidence_reader(args.evidence_dir)
            )
    elif name == "acceptance-show":
        result = service.show(args.operation)
    elif name == "acceptance-pending":
        result = service.pending()
    else:
        result = service.recover(args.operation)
    print(json.dumps(result, ensure_ascii=True, indent=2))
