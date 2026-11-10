"""Inspect and recover workflow state/events publication without reissuing consent."""

import json
from pathlib import Path
from uuid import UUID, uuid4
from product_strategy_agent.application.services.workflow_reopen_service import (
    WorkflowReopenService,
)
from product_strategy_agent.domain.projects.workflow_reopen import WorkflowReopen
from product_strategy_agent.domain.workflow.entities import WORKFLOW_STAGES
from product_strategy_agent.application.services.workflow_recovery_service import (
    WorkflowRecoveryService,
)
from product_strategy_agent.adapters.persistence.files.workflow_repository import (
    FileWorkflowStore,
)


def add_workflow_commands(commands):
    parser = commands.add_parser(
        "workflow", help="Inspect/recover interrupted workflow operations"
    )
    actions = parser.add_subparsers(dest="workflow_action", required=True)
    for name in ("pending", "recover", "review", "reopen"):
        action = actions.add_parser(name)
        action.add_argument("project_id")
        action.add_argument("--projects-dir", type=Path, default=Path("projects"))
        if name == "recover":
            action.add_argument("--operation", type=UUID, required=True)
        if name == "reopen":
            action.add_argument("--stage", required=True, choices=WORKFLOW_STAGES[:-1])
            action.add_argument("--by", required=True)
            action.add_argument("--reason", required=True)
            action.add_argument("--review-hash", required=True)
            action.add_argument("--expected-workflow-version", type=int, required=True)
            action.add_argument("--operation", type=UUID)


def handle_workflow_command(args):
    if args.workflow_action in {"review", "reopen"}:
        service = WorkflowReopenService(FileWorkflowStore(args.projects_dir))
        if args.workflow_action == "review":
            result = service.review(args.project_id)
        else:
            result = service.reopen(
                args.project_id,
                WorkflowReopen(
                    operation_id=args.operation or uuid4(),
                    target_stage=args.stage,
                    reopened_by=args.by,
                    reason=args.reason,
                    review_hash=args.review_hash,
                    expected_workflow_version=args.expected_workflow_version,
                ),
            )
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return
    service = WorkflowRecoveryService(FileWorkflowStore(args.projects_dir))
    if args.workflow_action == "recover":
        result = service.recover(args.project_id, args.operation)
    else:
        result = service.pending(args.project_id)
    print(json.dumps(result, ensure_ascii=True, indent=2))
