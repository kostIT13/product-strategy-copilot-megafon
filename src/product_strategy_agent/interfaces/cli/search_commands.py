"""CLI for project-scoped full-text search."""

import argparse
from dataclasses import asdict
import json

from product_strategy_agent.adapters.persistence.postgres.repositories.source_search import PostgresSourceSearch
from product_strategy_agent.application.services.source_search_service import SourceSearchService
from product_strategy_agent.domain.projects.errors import ProjectNotFound


def add_search_commands(commands: argparse._SubParsersAction) -> None:
    search = commands.add_parser("search", help="Search current source revisions")
    search.add_argument("project_key")
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=10)
    search.add_argument("--json", action="store_true")


def handle_search_command(args: argparse.Namespace) -> int:
    try:
        hits = SourceSearchService(PostgresSourceSearch()).search(args.project_key, args.query, args.limit)
        if args.json:
            print(json.dumps([asdict(hit) for hit in hits], default=str, ensure_ascii=False))
        else:
            for hit in hits:
                print(f"{hit.source_id} r{hit.revision} score={hit.score:.4f} {hit.title}\n{hit.uri}\n{hit.excerpt}\n")
            if not hits:
                print("No matching sources.")
        return 0
    except (ValueError, ProjectNotFound) as exc:
        print(f"Error: {exc}")
        return 2
