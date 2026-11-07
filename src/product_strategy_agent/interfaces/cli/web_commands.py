"""CLI for explicit import of public HTML/plain-text URLs."""
import argparse
from product_strategy_agent.adapters.web.fetcher import PublicWebFetcher
from product_strategy_agent.adapters.web.extractor import StaticWebPageExtractor
from product_strategy_agent.adapters.persistence.postgres.repositories.source_repository import PostgresSourceStore
from product_strategy_agent.application.services.source_service import SourceService
from product_strategy_agent.application.services.web_import_service import WebImportService
from product_strategy_agent.domain.projects.errors import ProjectNotFound


def add_web_commands(commands: argparse._SubParsersAction):
    web = commands.add_parser("web", help="Import public web sources")
    actions = web.add_subparsers(dest="action", required=True)
    importer = actions.add_parser("import", help="Fetch one public HTML or text URL")
    importer.add_argument("project_key")
    importer.add_argument("url")


def handle_web_command(args: argparse.Namespace) -> int:
    try:
        service = WebImportService(PublicWebFetcher(), StaticWebPageExtractor(), SourceService(PostgresSourceStore()))
        result = service.import_url(args.project_key, args.url)
        source = result.source
        print(f"Source {source.id} r{source.revision.revision}; new revision: {result.created_revision}")
        return 0
    except (ValueError, ProjectNotFound) as exc:
        print(f"Error: {exc}")
        return 2
