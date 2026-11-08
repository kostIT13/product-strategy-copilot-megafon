"""CLI for task-specific evidence drafts and project-scoped run inspection."""
import argparse
import json
from uuid import UUID

from product_strategy_agent.bootstrap import build_agent_service
from product_strategy_agent.interfaces.payloads import analysis_preview, agent_run_payload
from product_strategy_agent.domain.agent.models import AgentRunFailed
from product_strategy_agent.domain.projects.errors import ProjectNotFound
from product_strategy_agent.domain.agent.tasks import TASK_NAMES


def add_agent_commands(commands: argparse._SubParsersAction):
    agent = commands.add_parser("agent", help="Prepare checked evidence answers or extraction drafts")
    actions = agent.add_subparsers(dest="action", required=True)
    analyze = actions.add_parser("analyze", help="Retrieve sources and generate a citation-checked draft")
    analyze.add_argument("project_key")
    analyze.add_argument("--question", required=True)
    analyze.add_argument("--query", required=True, help="Full-text retrieval query")
    analyze.add_argument("--task", choices=TASK_NAMES, default="evidence_answer")
    analyze.add_argument("--dry-run", action="store_true", help="Print the request without calling the model or creating a run")
    show = actions.add_parser("show", help="Inspect a project-scoped agent run")
    show.add_argument("project_key")
    show.add_argument("run_id", type=UUID)


def handle_agent_command(args: argparse.Namespace) -> int:
    try:
        service = build_agent_service()
        if args.action == "show":
            output = agent_run_payload(service.get_run(args.project_key, args.run_id))
        elif args.dry_run:
            prepared = service.prepare(args.project_key, args.question, args.query, args.task)
            output = analysis_preview(prepared)
        else:
            output = agent_run_payload(service.analyze(args.project_key, args.question, args.query, args.task))
        print(json.dumps(output, default=str, ensure_ascii=False, indent=2))
        return 0
    except (AgentRunFailed, ProjectNotFound, ValueError) as exc:
        print(f"Error: {exc}")
        return 2
