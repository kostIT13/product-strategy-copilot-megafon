"""Read-only host inspection and plan; does not alter IDE configurations."""

import json
from pathlib import Path
from product_strategy_agent.interfaces.host_profiles import (
    host_profiles,
    parse_host_plan,
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


def handle_host_command(args):
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
