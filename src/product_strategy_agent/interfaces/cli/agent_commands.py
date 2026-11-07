"""CLI for preparing/reviewing and running the evidence-answer agent slice."""
import argparse
from dataclasses import asdict
import json
from uuid import UUID

from product_strategy_agent.adapters.llm.openai_compatible import OpenAICompatibleProvider
from product_strategy_agent.adapters.persistence.postgres.repositories.agent_run_repository import PostgresAgentRunStore
from product_strategy_agent.adapters.persistence.postgres.repositories.project_repository import PostgresProjectStore
from product_strategy_agent.adapters.persistence.postgres.repositories.source_repository import PostgresSourceStore
from product_strategy_agent.adapters.persistence.postgres.repositories.source_search import PostgresSourceSearch
from product_strategy_agent.application.services.agent_analysis_service import AgentAnalysisService
from product_strategy_agent.application.services.source_search_service import SourceSearchService
from product_strategy_agent.config import get_settings
from product_strategy_agent.domain.agent.models import AgentRunFailed
from product_strategy_agent.domain.projects.errors import ProjectNotFound


def build_agent_service() -> AgentAnalysisService:
    return AgentAnalysisService(PostgresProjectStore(), PostgresSourceStore(),
        SourceSearchService(PostgresSourceSearch()), OpenAICompatibleProvider(get_settings()), PostgresAgentRunStore())


def add_agent_commands(commands: argparse._SubParsersAction):
    agent = commands.add_parser("agent", help="Prepare draft answers from imported evidence")
    actions = agent.add_subparsers(dest="action", required=True)
    analyze = actions.add_parser("analyze", help="Retrieve sources and generate a citation-checked draft")
    analyze.add_argument("project_key")
    analyze.add_argument("--question", required=True)
    analyze.add_argument("--query", required=True, help="Full-text retrieval query")
    analyze.add_argument("--dry-run", action="store_true", help="Print the request without calling the model or creating a run")
    show = actions.add_parser("show", help="Inspect a project-scoped agent run")
    show.add_argument("project_key")
    show.add_argument("run_id", type=UUID)


def handle_agent_command(args: argparse.Namespace) -> int:
    try:
        service = build_agent_service()
        if args.action == "show":
            output = asdict(service.get_run(args.project_key, args.run_id))
        elif args.dry_run:
            prepared = service.prepare(args.project_key, args.question, args.query)
            output = {"dry_run": True, "model": prepared.model, "prompt_version": prepared.prompt_version,
                      "messages": prepared.messages,
                      "contexts": [{key: value for key, value in context.items() if key != "text"} for context in prepared.contexts]}
        else:
            output = asdict(service.analyze(args.project_key, args.question, args.query))
        print(json.dumps(output, default=str, ensure_ascii=False, indent=2))
        return 0
    except (AgentRunFailed, ProjectNotFound, ValueError) as exc:
        print(f"Error: {exc}")
        return 2
