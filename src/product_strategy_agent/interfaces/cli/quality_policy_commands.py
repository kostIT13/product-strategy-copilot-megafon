"""Inspect a case policy or explicitly enable required reviews for a legacy snapshot."""

import json
from pathlib import Path
from uuid import UUID, uuid4
from pydantic import ValidationError
from product_strategy_agent.adapters.persistence.files.quality_policy_store import (
    FileQualityPolicyStore,
)
from product_strategy_agent.application.services.quality_policy_service import (
    QualityPolicyService,
)
from product_strategy_agent.domain.projects.quality_policy import EnableQualityPolicy


def add_quality_policy_commands(commands):
    parser = commands.add_parser(
        "policy", help="inspect/enable required semantic review policy"
    )
    actions = parser.add_subparsers(dest="policy_action", required=True)
    for name in ("show", "enable"):
        action = actions.add_parser(name)
        action.add_argument("project_id")
        action.add_argument("--projects-dir", type=Path, default=Path("projects"))
        if name == "enable":
            action.add_argument("--by", required=True)
            action.add_argument("--reason", required=True)
            action.add_argument("--review-hash", required=True)
            action.add_argument("--expected-workflow-version", type=int, required=True)
            action.add_argument("--operation", type=UUID)


def handle_quality_policy_command(args):
    service = QualityPolicyService(FileQualityPolicyStore(args.projects_dir))
    if args.policy_action == "show":
        result = service.show(args.project_id)
    else:
        try:
            command = EnableQualityPolicy(
                operation_id=args.operation or uuid4(),
                enabled_by=args.by,
                reason=args.reason,
                review_hash=args.review_hash,
                expected_workflow_version=args.expected_workflow_version,
            )
        except ValidationError:
            raise ValueError("invalid quality policy enablement fields") from None
        result = service.enable(args.project_id, command)
    print(json.dumps(result, ensure_ascii=True, indent=2))
