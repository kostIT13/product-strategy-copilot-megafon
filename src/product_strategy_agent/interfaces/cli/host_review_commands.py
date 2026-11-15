"""Explicit report assessment and disabled configuration preview commands."""

import json
from pathlib import Path
import sys
from uuid import UUID
from product_strategy_agent.interfaces.host_profiles import parse_host_plan
from product_strategy_agent.interfaces.host_reviews import host_reviews, host_preview
from product_strategy_agent.domain.automation.host_reviews import parse_review_request


def add_review_actions(actions):
    for name in (
        "review-prepare",
        "review-record",
        "review-show",
        "review-pending",
        "review-recover",
        "preview-codex",
    ):
        action = actions.add_parser(name)
        action.add_argument("--instructions-root", type=Path, default=Path("."))
        if name in ("review-record", "preview-codex"):
            action.add_argument("--request", type=Path, required=True)
        if name in ("review-show", "review-recover"):
            action.add_argument("--operation", type=UUID, required=True)
        if name == "review-prepare":
            action.add_argument("--report", type=UUID, required=True)
            action.add_argument("--include-evidence", action="store_true")
        if name == "preview-codex":
            action.add_argument(
                "--interpreter", type=Path, default=Path(sys.executable)
            )
            action.add_argument("--review", type=UUID)


def handle_review_command(args):
    service = host_reviews(args.instructions_root)
    name = args.host_action
    if name in ("review-record", "preview-codex"):
        with args.request.open("rb") as stream:
            raw = stream.read(64001)
        if name == "review-record":
            result = service.record(parse_review_request(raw))
        else:
            result = host_preview(args.instructions_root).preview(
                parse_host_plan(raw), args.interpreter, args.review
            )
    elif name == "review-prepare":
        result = service.prepare(args.report, args.include_evidence)
    elif name == "review-show":
        result = service.show(args.operation)
    elif name == "review-pending":
        result = service.pending()
    else:
        result = service.recover(args.operation)
    print(json.dumps(result, ensure_ascii=True, indent=2))
