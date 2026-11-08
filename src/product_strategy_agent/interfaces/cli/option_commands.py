"""CLI commands for strategic alternatives."""

import argparse
from uuid import UUID

from product_strategy_agent.adapters.persistence.postgres.repositories.claim_repository import PostgresClaimStore
from product_strategy_agent.adapters.persistence.postgres.repositories.option_repository import PostgresOptionStore
from product_strategy_agent.adapters.persistence.postgres.repositories.project_repository import PostgresProjectStore
from product_strategy_agent.application.services.option_service import OptionService
from product_strategy_agent.domain.decisions.entities import OptionClaim
from product_strategy_agent.domain.decisions.errors import InvalidOption, OptionAlreadyExists
from product_strategy_agent.domain.projects.errors import ProjectNotFound


def add_option_commands(commands: argparse._SubParsersAction) -> None:
    option = commands.add_parser("option", help="Manage strategy alternatives")
    actions = option.add_subparsers(dest="action", required=True)
    add = actions.add_parser("add", help="Add an alternative")
    add.add_argument("project_key")
    add.add_argument("--key", required=True)
    add.add_argument("--name", required=True)
    add.add_argument("--description")
    add.add_argument("--strength", action="append", default=[])
    add.add_argument("--risk", action="append", default=[])
    add.add_argument("--assumption", action="append", default=[])
    add.add_argument("--supports", action="append", default=[], metavar="CLAIM_UUID")
    add.add_argument("--challenges", action="append", default=[], metavar="CLAIM_UUID")
    listing = actions.add_parser("list", help="List alternatives")
    listing.add_argument("project_key")


def handle_option_command(args: argparse.Namespace) -> int:
    service = OptionService(PostgresOptionStore(), PostgresProjectStore(), PostgresClaimStore())
    try:
        if args.action == "list":
            options = service.list_for_project(args.project_key)
            for option in options:
                print(f"{option.key}  {option.status}  {option.name}")
            if not options:
                print("No options registered.")
            return 0
        links = tuple(
            [OptionClaim(UUID(claim_id), "supports") for claim_id in args.supports]
            + [OptionClaim(UUID(claim_id), "challenges") for claim_id in args.challenges]
        )
        option = service.create(
            project_key=args.project_key,
            key=args.key,
            name=args.name,
            description=args.description,
            strengths=tuple(args.strength),
            risks=tuple(args.risk),
            assumptions=tuple(args.assumption),
            claim_links=links,
        )
        print(f"Created option {option.key} ({option.id})")
        return 0
    except (InvalidOption, OptionAlreadyExists, ProjectNotFound, ValueError) as exc:
        print(f"Error: {exc}")
        return 2
