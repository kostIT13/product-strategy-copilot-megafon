"""Explicit source withdrawal and read-only dependency impact."""

import json
from pathlib import Path
from uuid import UUID, uuid4
from product_strategy_agent.adapters.persistence.files.workflow_repository import (
    FileWorkflowStore,
)
from product_strategy_agent.application.services.source_lifecycle_service import (
    SourceLifecycleService,
)
from product_strategy_agent.domain.projects.source_lifecycle import SourceWithdrawal


def add_source_lifecycle_commands(commands):
    for name in ("withdraw", "impact"):
        parser = commands.add_parser(name)
        parser.add_argument("project_id")
        parser.add_argument("--projects-dir", type=Path, default=Path("projects"))
        if name == "withdraw":
            parser.add_argument("source_id")
            parser.add_argument("--by", required=True)
            parser.add_argument("--reason", required=True)
            parser.add_argument("--operation", type=UUID)
            parser.add_argument("--expected-workflow-version", type=int)


def handle_source_lifecycle_command(args):
    service = SourceLifecycleService(FileWorkflowStore(args.projects_dir))
    if args.source_command == "impact":
        result = service.impact(args.project_id)
    else:
        result = service.withdraw(
            args.project_id,
            SourceWithdrawal(
                operation_id=args.operation or uuid4(),
                source_id=args.source_id,
                withdrawn_by=args.by,
                reason=args.reason,
                expected_workflow_version=args.expected_workflow_version,
            ),
        )
    print(json.dumps(result, ensure_ascii=True, indent=2))
