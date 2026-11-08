"""CLI commands for product capabilities."""

import argparse
from dataclasses import asdict
import json
from uuid import UUID

from product_strategy_agent.adapters.persistence.postgres.repositories.capability_repository import (
    PostgresCapabilityStore,
)
from product_strategy_agent.adapters.persistence.postgres.repositories.claim_repository import PostgresClaimStore
from product_strategy_agent.adapters.persistence.postgres.repositories.project_repository import PostgresProjectStore
from product_strategy_agent.application.services.capability_service import CapabilityService
from product_strategy_agent.domain.capabilities.errors import CapabilityAlreadyExists, InvalidCapability
from product_strategy_agent.domain.projects.errors import ProjectNotFound
from product_strategy_agent.interfaces.payloads import json_payload


def add_capability_commands(commands: argparse._SubParsersAction) -> None:
    capability = commands.add_parser("capability", help="Manage product capabilities")
    actions = capability.add_subparsers(dest="action", required=True)
    add = actions.add_parser("add", help="Register a product capability")
    add.add_argument("project_key")
    add.add_argument("--key", required=True)
    add.add_argument("--name", required=True)
    add.add_argument("--status", required=True, choices=("available", "planned", "unavailable"))
    add.add_argument("--claim", action="append", default=[], metavar="CLAIM_UUID")
    add.add_argument("--description")
    listing = actions.add_parser("list", help="List product capabilities")
    listing.add_argument("project_key")
    listing.add_argument("--json", action="store_true", help="Machine-readable UUIDs and linked claim IDs")


def handle_capability_command(args: argparse.Namespace) -> int:
    service = CapabilityService(PostgresCapabilityStore(), PostgresProjectStore(), PostgresClaimStore())
    try:
        if args.action == "list":
            items = service.list_for_project(args.project_key)
            if getattr(args, "json", False):
                print(json.dumps(json_payload([asdict(item) for item in items]), ensure_ascii=False, indent=2))
                return 0
            for item in items:
                print(f"{item.key}  {item.status}  {item.name}  (claims: {len(item.claim_ids)})")
            if not items:
                print("No capabilities registered.")
            return 0
        item = service.create(
            project_key=args.project_key,
            key=args.key,
            name=args.name,
            status=args.status,
            claim_ids=tuple(UUID(value) for value in args.claim),
            description=args.description,
        )
        print(f"Created capability {item.key} ({item.status})")
        return 0
    except (CapabilityAlreadyExists, InvalidCapability, ProjectNotFound, ValueError) as exc:
        print(f"Error: {exc}")
        return 2
