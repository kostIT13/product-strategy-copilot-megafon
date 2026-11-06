"""CLI commands for human-owned decisions."""

import argparse
from uuid import UUID

from product_strategy_agent.adapters.persistence.postgres.repositories.claim_repository import PostgresClaimStore
from product_strategy_agent.adapters.persistence.postgres.repositories.decision_repository import PostgresDecisionStore
from product_strategy_agent.adapters.persistence.postgres.repositories.option_repository import PostgresOptionStore
from product_strategy_agent.adapters.persistence.postgres.repositories.project_repository import PostgresProjectStore
from product_strategy_agent.application.services.decision_service import DecisionService
from product_strategy_agent.domain.decisions.errors import DecisionAlreadyExists, InvalidDecision
from product_strategy_agent.domain.projects.errors import ProjectNotFound


def add_decision_commands(commands: argparse._SubParsersAction) -> None:
    decision = commands.add_parser("decision", help="Record human decisions")
    actions = decision.add_subparsers(dest="action", required=True)
    add = actions.add_parser("add", help="Record a decision and review conditions")
    add.add_argument("project_key")
    add.add_argument("--key", required=True)
    add.add_argument("--selected-option", required=True, metavar="OPTION_UUID")
    add.add_argument("--owner", required=True)
    add.add_argument("--rationale", required=True)
    add.add_argument("--review-trigger", required=True)
    add.add_argument("--claim", action="append", default=[], metavar="CLAIM_UUID")
    add.add_argument("--reject-option", action="append", default=[], metavar="OPTION_UUID")
    add.add_argument("--defer-option", action="append", default=[], metavar="OPTION_UUID")
    add.add_argument("--assumption", action="append", default=[])
    add.add_argument("--risk", action="append", default=[])
    listing = actions.add_parser("list", help="List recorded decisions")
    listing.add_argument("project_key")


def handle_decision_command(args: argparse.Namespace) -> int:
    service = DecisionService(
        PostgresDecisionStore(),
        PostgresProjectStore(),
        PostgresOptionStore(),
        PostgresClaimStore(),
    )
    try:
        if args.action == "list":
            decisions = service.list_for_project(args.project_key)
            for decision in decisions:
                print(
                    f"{decision.key}  selected={decision.selected_option_id}  "
                    f"owner={decision.owner}  review={decision.review_trigger}"
                )
            if not decisions:
                print("No decisions recorded.")
            return 0
        decision = service.create(
            project_key=args.project_key,
            key=args.key,
            selected_option_id=UUID(args.selected_option),
            owner=args.owner,
            rationale=args.rationale,
            review_trigger=args.review_trigger,
            basis_claim_ids=tuple(UUID(item) for item in args.claim),
            rejected_option_ids=tuple(UUID(item) for item in args.reject_option),
            deferred_option_ids=tuple(UUID(item) for item in args.defer_option),
            assumptions=tuple(args.assumption),
            risks=tuple(args.risk),
        )
        print(f"Recorded decision {decision.key} ({decision.id})")
        return 0
    except (DecisionAlreadyExists, InvalidDecision, ProjectNotFound, ValueError) as exc:
        print(f"Error: {exc}")
        return 2
