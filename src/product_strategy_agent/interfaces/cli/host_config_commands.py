"""Explicit plan/apply/inspect/recover for disabled-only project config changes."""

import json
from pathlib import Path
from uuid import UUID
from product_strategy_agent.interfaces.host_config import host_config
from product_strategy_agent.domain.automation.host_config import (
    PlanConfigChange,
    ApplyConfigChange,
    parse_request,
)


def add_config_actions(actions):
    for name in (
        "config-plan",
        "config-apply",
        "config-show",
        "config-pending",
        "config-audit",
        "config-recover",
    ):
        action = actions.add_parser(name)
        action.add_argument("--instructions-root", type=Path, default=Path("."))
        if name in ("config-plan", "config-apply"):
            action.add_argument("--request", type=Path, required=True)
        if name in ("config-show", "config-recover"):
            action.add_argument("--operation", type=UUID, required=True)


def handle_config_command(args):
    service = host_config(args.instructions_root)
    name = args.host_action
    if name in ("config-plan", "config-apply"):
        with args.request.open("rb") as stream:
            raw = stream.read(64001)
        result = (
            service.plan(parse_request(raw, PlanConfigChange))
            if name == "config-plan"
            else service.apply(parse_request(raw, ApplyConfigChange))
        )
    elif name == "config-show":
        result = service.show(args.operation)
    elif name == "config-pending":
        result = service.pending()
    elif name == "config-audit":
        result = service.audit()
    else:
        result = service.recover(args.operation)
    print(json.dumps(result, ensure_ascii=True, indent=2))
