"""Entry point for the PostgreSQL-backed main application CLI."""

import argparse
import sys
from product_strategy_agent.interfaces.cli.promise_commands import add_promise_commands, handle_promise_command
from product_strategy_agent.interfaces.cli.strategy_commands import add_strategy_commands, handle_strategy_command
from product_strategy_agent.interfaces.cli.selection_commands import add_selection_commands, handle_selection_command
from product_strategy_agent.interfaces.cli.critic_commands import add_critic_commands, handle_critic_command
from product_strategy_agent.interfaces.cli.pipeline_commands import add_pipeline_commands, handle_pipeline_command
from product_strategy_agent.interfaces.cli.agent_commands import add_agent_commands, handle_agent_command
from product_strategy_agent.interfaces.cli.web_commands import add_web_commands, handle_web_command
from product_strategy_agent.interfaces.cli.search_commands import add_search_commands, handle_search_command
from product_strategy_agent.interfaces.cli.document_commands import add_document_commands, handle_document_command
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
from product_strategy_agent.interfaces.cli.workflow_commands import (
    add_workflow_commands,
    handle_workflow_command,
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
    add_workflow_commands(commands)
    add_document_commands(commands)
    add_search_commands(commands)
    add_web_commands(commands)
    add_agent_commands(commands)
    add_pipeline_commands(commands)
    add_critic_commands(commands)
    add_selection_commands(commands)
    add_strategy_commands(commands)
    add_promise_commands(commands)
    return parser


def main() -> int:
    # JSON exports must retain UTF-8 when stdout is redirected on Windows.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = build_parser().parse_args()
    handlers: dict[str, Callable[[Any], int]] = {
        "project": handle_project_command,
        "source": handle_source_command,
        "claim": handle_claim_command,
        "option": handle_option_command,
        "decision": handle_decision_command,
        "capability": handle_capability_command,
        "workflow": handle_workflow_command,
        "document": handle_document_command,
        "search": handle_search_command,
        "web": handle_web_command,
        "agent": handle_agent_command,
        "pipeline": handle_pipeline_command,
        "critic": handle_critic_command,
        "selection": handle_selection_command,
        "strategy": handle_strategy_command,
        "promise": handle_promise_command,
    }
    return handlers[args.resource](args)


if __name__ == "__main__":
    raise SystemExit(main())
