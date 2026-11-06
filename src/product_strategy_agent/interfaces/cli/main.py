"""Entry point for the PostgreSQL-backed main application CLI."""

import argparse
from collections.abc import Callable
from typing import Any

from product_strategy_agent.interfaces.cli.project_commands import (
    add_project_commands,
    handle_project_command,
)
from product_strategy_agent.interfaces.cli.decision_commands import (
    add_decision_commands,
    handle_decision_command,
)
from product_strategy_agent.interfaces.cli.option_commands import (
    add_option_commands,
    handle_option_command,
)
from product_strategy_agent.interfaces.cli.claim_commands import (
    add_claim_commands,
    handle_claim_command,
)
from product_strategy_agent.interfaces.cli.capability_commands import (
    add_capability_commands,
    handle_capability_command,
)
from product_strategy_agent.interfaces.cli.source_commands import (
    add_source_commands,
    handle_source_command,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="psa-main", description="Main PostgreSQL-backed product strategy application")
    commands = parser.add_subparsers(dest="resource", required=True)
    add_project_commands(commands)
    add_source_commands(commands)
    add_claim_commands(commands)
    add_option_commands(commands)
    add_decision_commands(commands)
    add_capability_commands(commands)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    handlers: dict[str, Callable[[Any], int]] = {
        "project": handle_project_command,
        "source": handle_source_command,
        "claim": handle_claim_command,
        "option": handle_option_command,
        "decision": handle_decision_command,
        "capability": handle_capability_command,
    }
    return handlers[args.resource](args)


if __name__ == "__main__":
    raise SystemExit(main())
