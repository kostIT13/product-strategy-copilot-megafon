"""CLI commands for registering project source text and its revisions."""

import argparse
from pathlib import Path

from product_strategy_agent.adapters.persistence.postgres.repositories.source_repository import (
    PostgresSourceStore,
)
from product_strategy_agent.application.services.source_service import SourceService
from product_strategy_agent.domain.projects.errors import ProjectNotFound
from product_strategy_agent.domain.sources.errors import InvalidSource


def add_source_commands(commands: argparse._SubParsersAction) -> None:
    source = commands.add_parser("source", help="Manage project sources")
    actions = source.add_subparsers(dest="action", required=True)

    add = actions.add_parser("add", help="Register extracted text from a UTF-8 file")
    add.add_argument("project_key")
    add.add_argument("file", type=Path)
    add.add_argument("--uri", help="Canonical source URL or path; defaults to the given file path")
    add.add_argument(
        "--kind",
        choices=("local_text", "web_page", "uploaded_document", "dataset"),
        default="local_text",
    )
    add.add_argument("--title")
    add.add_argument("--publisher")

    list_command = actions.add_parser("list", help="List project sources")
    list_command.add_argument("project_key")


def handle_source_command(args: argparse.Namespace) -> int:
    try:
        service = SourceService(PostgresSourceStore())
        if args.action == "list":
            sources = service.list_for_project(args.project_key)
            for source in sources:
                print(
                    f"{source.id}  r{source.revision.revision}  {source.kind}  "
                    f"{source.revision.content_hash}  {source.uri}"
                )
            if not sources:
                print("No sources registered.")
            return 0

        path = args.file.expanduser().resolve(strict=True)
        if not path.is_file():
            raise InvalidSource(f"source file is not a regular file: {path}")
        if path.stat().st_size > 10 * 1024 * 1024:
            raise InvalidSource("source file exceeds the 10 MiB limit")
        text = path.read_text(encoding="utf-8-sig")
        result = service.register(
            project_key=args.project_key,
            uri=args.uri or str(path),
            kind=args.kind,
            extracted_text=text,
            title=args.title,
            publisher=args.publisher,
        )
        verb = "Recorded" if result.created_revision else "Already registered"
        source = result.source
        print(
            f"{verb} source '{source.uri}' revision {source.revision.revision} "
            f"(sha256:{source.revision.content_hash})"
        )
        return 0
    except (InvalidSource, ProjectNotFound, OSError, UnicodeError) as exc:
        print(f"Error: {exc}")
        return 2
