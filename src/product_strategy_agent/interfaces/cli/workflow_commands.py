"""CLI commands for workflow initialization, approvals, and history."""

import argparse

from product_strategy_agent.adapters.persistence.postgres.repositories.project_repository import PostgresProjectStore
from product_strategy_agent.adapters.persistence.postgres.repositories.workflow_repository import PostgresWorkflowStore
from product_strategy_agent.application.services.workflow_service import WorkflowService
from product_strategy_agent.domain.projects.errors import ProjectNotFound
from product_strategy_agent.domain.workflow.errors import WorkflowError


def add_workflow_commands(commands: argparse._SubParsersAction) -> None:
    workflow = commands.add_parser("workflow", help="Manage project workflow")
    actions = workflow.add_subparsers(dest="action", required=True)
    start = actions.add_parser("start", help="Initialize the workflow at intake")
    start.add_argument("project_key")
    start.add_argument("--by", required=True, dest="actor")
    start.add_argument("--reason", default="")
    status = actions.add_parser("status", help="Show current stage and next stage")
    status.add_argument("project_key")
    advance = actions.add_parser("advance", help="Approve the current stage and advance")
    advance.add_argument("project_key")
    advance.add_argument("--approved-by", required=True, dest="actor")
    advance.add_argument("--reason", required=True)
    events = actions.add_parser("events", help="Show transition history")
    events.add_argument("project_key")


def handle_workflow_command(args: argparse.Namespace) -> int:
    service = WorkflowService(PostgresWorkflowStore(), PostgresProjectStore())
    try:
        if args.action == "start":
            state = service.start(args.project_key, args.actor, args.reason)
            print(f"Workflow started at {state.current_stage} (version {state.version})")
            return 0
        if args.action == "status":
            state, next_stage = service.status(args.project_key)
            print(
                f"Stage: {state.current_stage}\nStatus: {state.status}\n"
                f"Next: {next_stage or 'none'}\nVersion: {state.version}\nUpdated: {state.updated_at.isoformat()}"
            )
            return 0
        if args.action == "advance":
            state = service.advance(args.project_key, args.actor, args.reason)
            print(f"Approved; workflow advanced to {state.current_stage} (version {state.version})")
            return 0
        for event in service.history(args.project_key):
            previous = event.from_stage or "start"
            print(
                f"#{event.sequence} {previous} -> {event.to_stage}  "
                f"by {event.actor}  {event.occurred_at.isoformat()}  {event.reason}"
            )
        return 0
    except (WorkflowError, ProjectNotFound, ValueError) as exc:
        print(f"Error: {exc}")
        return 2
