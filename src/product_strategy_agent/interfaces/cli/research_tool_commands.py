"""Read-only registry navigation independent of case selection."""

import json

from product_strategy_agent.application.services.research_tool_registry_service import (
    ResearchToolRegistryService,
)


def add_research_tool_commands(commands):
    parser = commands.add_parser(
        "tools",
        help="inspect shipped research capabilities; never execute or authorize",
    )
    actions = parser.add_subparsers(dest="tools_action", required=True)
    actions.add_parser("list")
    describe = actions.add_parser("describe")
    describe.add_argument("tool_id")


def handle_research_tool_command(args):
    result = ResearchToolRegistryService().describe(getattr(args, "tool_id", None))
    print(json.dumps(result, ensure_ascii=True, indent=2))
