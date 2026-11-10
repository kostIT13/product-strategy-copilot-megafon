"""Explicit human withdrawal and read-only dependency impact."""

import json
from pathlib import Path
from uuid import UUID, uuid4
from product_strategy_agent.adapters.persistence.files.workflow_repository import (
    FileWorkflowStore,
)
from product_strategy_agent.application.services.claim_lifecycle_service import (
    ClaimLifecycleService,
)
from product_strategy_agent.domain.projects.claim_lifecycle import ClaimWithdrawal


def add_claim_lifecycle_commands(commands):
    for name in ("withdraw", "impact"):
        parser = commands.add_parser(name)
        parser.add_argument("project_id")
        parser.add_argument("--projects-dir", type=Path, default=Path("projects"))
        if name == "withdraw":
            parser.add_argument("claim_id")
            parser.add_argument("--by", required=True)
            parser.add_argument("--reason", required=True)
            parser.add_argument("--operation", type=UUID)
            parser.add_argument("--expected-workflow-version", type=int)


def handle_claim_lifecycle_command(args):
    service = ClaimLifecycleService(FileWorkflowStore(args.projects_dir))
    result = (
        service.impact(args.project_id)
        if args.claim_command == "impact"
        else service.withdraw(
            args.project_id,
            ClaimWithdrawal(
                operation_id=args.operation or uuid4(),
                claim_id=args.claim_id,
                withdrawn_by=args.by,
                reason=args.reason,
                expected_workflow_version=args.expected_workflow_version,
            ),
        )
    )
    print(json.dumps(result, ensure_ascii=True, indent=2))
