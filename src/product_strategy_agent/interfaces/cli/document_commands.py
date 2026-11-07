"""CLI for extracting local documents and registering source revisions."""

import argparse
from pathlib import Path

from product_strategy_agent.adapters.documents.local import LocalDocumentExtractor
from product_strategy_agent.adapters.persistence.postgres.repositories.source_repository import PostgresSourceStore
from product_strategy_agent.application.services.document_import_service import DocumentImportService
from product_strategy_agent.application.services.source_service import SourceService
from product_strategy_agent.domain.projects.errors import ProjectNotFound


def add_document_commands(commands: argparse._SubParsersAction) -> None:
    document = commands.add_parser("document", help="Import local documents")
    actions = document.add_subparsers(dest="action", required=True)
    importer = actions.add_parser("import", help="Extract a local text, HTML, DOCX, PDF, or XLSX document")
    importer.add_argument("project_key")
    importer.add_argument("file", type=Path)
    importer.add_argument("--uri")
    importer.add_argument("--title")
    importer.add_argument("--publisher")
    importer.add_argument("--encoding", default="utf-8-sig")


def handle_document_command(args: argparse.Namespace) -> int:
    service = DocumentImportService(LocalDocumentExtractor(), SourceService(PostgresSourceStore()))
    try:
        result = service.import_file(args.project_key, args.file, uri=args.uri, title=args.title,
                                     publisher=args.publisher, encoding=args.encoding)
        source = result.source
        print(f"Source {source.id} revision {source.revision.revision}; new revision: {result.created_revision}")
        return 0
    except (OSError, ValueError, ProjectNotFound) as exc:
        print(f"Error: {exc}")
        return 2
