"""CLI commands for claims and citation-checked evidence."""

import argparse
from dataclasses import asdict
import json
from uuid import UUID

from product_strategy_agent.adapters.persistence.postgres.repositories.claim_repository import (
    PostgresClaimStore,
)
from product_strategy_agent.adapters.persistence.postgres.repositories.project_repository import (
    PostgresProjectStore,
)
from product_strategy_agent.adapters.persistence.postgres.repositories.source_repository import (
    PostgresSourceStore,
)
from product_strategy_agent.application.services.claim_service import ClaimService
from product_strategy_agent.domain.evidence.entities import EvidenceReference
from product_strategy_agent.domain.evidence.errors import ClaimAlreadyExists, InvalidClaim
from product_strategy_agent.domain.projects.errors import ProjectNotFound
from product_strategy_agent.interfaces.payloads import json_payload


def add_claim_commands(commands: argparse._SubParsersAction) -> None:
    claim = commands.add_parser("claim", help="Manage evidence-backed claims")
    actions = claim.add_subparsers(dest="action", required=True)

    add = actions.add_parser("add", help="Add a claim")
    add.add_argument("project_key")
    add.add_argument("--key", required=True)
    add.add_argument("--type", dest="claim_type", required=True,
                      choices=("fact", "interpretation", "hypothesis", "forecast", "synthetic"))
    add.add_argument("--text", required=True)
    add.add_argument("--confidence", required=True, choices=("low", "medium", "high"))
    add.add_argument(
        "--evidence",
        action="append",
        nargs=4,
        metavar=("SOURCE_ID", "REVISION", "LOCATOR", "QUOTE"),
        help="Repeat for each citation to a source revision",
    )
    add.add_argument("--reasoning-note")
    add.add_argument("--decision-impact")

    listing = actions.add_parser("list", help="List project claims")
    listing.add_argument("project_key")
    listing.add_argument("--json", action="store_true", help="Machine-readable claim UUIDs, types and evidence references")


def handle_claim_command(args: argparse.Namespace) -> int:
    service = ClaimService(
        claims=PostgresClaimStore(),
        projects=PostgresProjectStore(),
        sources=PostgresSourceStore(),
    )
    try:
        if args.action == "list":
            claims = service.list_for_project(args.project_key)
            if getattr(args, "json", False):
                print(json.dumps(json_payload([asdict(claim) for claim in claims]), ensure_ascii=False, indent=2))
                return 0
            for claim in claims:
                print(
                    f"{claim.key}  [{claim.claim_type}/{claim.confidence}]  "
                    f"{claim.text}  (citations: {len(claim.evidence)})"
                )
            if not claims:
                print("No claims registered.")
            return 0

        evidence = tuple(
            EvidenceReference(
                source_id=UUID(source_id),
                source_revision=int(revision),
                locator=locator,
                quote=quote,
            )
            for source_id, revision, locator, quote in (args.evidence or [])
        )
        claim = service.create(
            project_key=args.project_key,
            key=args.key,
            text=args.text,
            claim_type=args.claim_type,
            confidence=args.confidence,
            evidence=evidence,
            reasoning_note=args.reasoning_note,
            decision_impact=args.decision_impact,
        )
        print(f"Created claim {claim.key} ({claim.id}); citations: {len(claim.evidence)}")
        return 0
    except (ClaimAlreadyExists, InvalidClaim, ProjectNotFound, ValueError) as exc:
        print(f"Error: {exc}")
        return 2
