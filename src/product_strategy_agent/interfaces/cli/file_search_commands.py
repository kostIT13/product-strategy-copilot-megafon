"""Read-only source search CLI over the shared file retrieval service."""

import json
from pathlib import Path
from product_strategy_agent.adapters.persistence.files.source_search_repository import (
    FileSourceSearchStore,
)
from product_strategy_agent.application.services.file_source_search_service import (
    FileSourceSearchService,
)


def add_file_search_command(commands):
    parser = commands.add_parser(
        "search", help="search checked current source text without network or SQL"
    )
    parser.add_argument("project_id")
    parser.add_argument("query")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--projects-dir", type=Path, default=Path("projects"))


def handle_file_search_command(args):
    result = FileSourceSearchService(FileSourceSearchStore(args.projects_dir)).search(
        args.project_id, args.query, args.limit
    )
    print(json.dumps(result, ensure_ascii=True, indent=2))
