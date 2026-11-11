"""Prepare a review packet; record only an explicitly supplied human assessment."""

import json
from pathlib import Path
from uuid import UUID, uuid4
from pydantic import ValidationError
from product_strategy_agent.adapters.persistence.files.semantic_review_store import (
    FileSemanticReviewStore,
)
from product_strategy_agent.application.services.semantic_review_service import (
    SemanticReviewService,
)
from product_strategy_agent.domain.projects.semantic_review import SemanticReview
from product_strategy_agent.domain.projects.validation_plan import (
    unique_object,
    reject_constant,
)


def add_semantic_review_commands(commands):
    parser = commands.add_parser(
        "review", help="prepare/record human semantic assessments"
    )
    actions = parser.add_subparsers(dest="review_action", required=True)
    for name in ("prepare", "record"):
        action = actions.add_parser(name)
        action.add_argument("project_id")
        action.add_argument(
            "--scope", required=True, choices=("strategy", "validation")
        )
        action.add_argument("--projects-dir", type=Path, default=Path("projects"))
        if name == "record":
            action.add_argument("--by", required=True)
            action.add_argument("--reason", required=True)
            action.add_argument(
                "--verdict", required=True, choices=("accepted", "changes_requested")
            )
            action.add_argument("--checks", type=Path, required=True)
            action.add_argument("--review-hash", required=True)
            action.add_argument("--expected-workflow-version", type=int, required=True)
            action.add_argument("--operation", type=UUID)


def handle_semantic_review_command(args):
    service = SemanticReviewService(FileSemanticReviewStore(args.projects_dir))
    if args.review_action == "prepare":
        result = service.prepare(args.project_id, args.scope)
    else:
        with args.checks.open("rb") as stream:
            raw = stream.read(64001)
        if len(raw) > 64000:
            raise ValueError("review checklist exceeds 64000 bytes")
        try:
            checks = json.loads(
                raw.decode("utf-8-sig"),
                object_pairs_hook=unique_object,
                parse_constant=reject_constant,
            )
            command = SemanticReview(
                operation_id=args.operation or uuid4(),
                scope=args.scope,
                reviewed_by=args.by,
                reason=args.reason,
                verdict=args.verdict,
                checks=checks,
                review_hash=args.review_hash,
                expected_workflow_version=args.expected_workflow_version,
            )
        except ValidationError:
            raise ValueError("invalid semantic assessment fields/checklist") from None
        except RecursionError:
            raise ValueError(
                "semantic checklist JSON nesting exceeds parser limit"
            ) from None
        result = service.record(args.project_id, command)
    print(json.dumps(result, ensure_ascii=True, indent=2))
