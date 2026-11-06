"""Entry point for the PostgreSQL-backed main application CLI."""

import argparse

from product_strategy_agent.adapters.persistence.postgres.repositories.project_repository import (
    PostgresProjectStore,
)
from product_strategy_agent.application.services.project_service import ProjectService
from product_strategy_agent.domain.projects.errors import (
    ProjectAlreadyExists,
    ProjectNotFound,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="psa-main", description="Main PostgreSQL-backed product strategy application")
    commands = parser.add_subparsers(dest="resource", required=True)
    project = commands.add_parser("project", help="Manage projects")
    actions = project.add_subparsers(dest="action", required=True)

    create = actions.add_parser("create", help="Create a project")
    create.add_argument("--key", required=True)
    create.add_argument("--name", required=True)
    create.add_argument("--description")

    show = actions.add_parser("show", help="Show a project")
    show.add_argument("key")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    projects = ProjectService(PostgresProjectStore())

    try:
        if args.resource == "project" and args.action == "create":
            project = projects.create(args.key, args.name, args.description)
            print(f"Created project '{project.key}' ({project.id})")
            return 0

        if args.resource == "project" and args.action == "show":
            project = projects.get(args.key)
            print(f"Key: {project.key}\nName: {project.name}\nStatus: {project.status}\nID: {project.id}")
            if project.description:
                print(f"Description: {project.description}")
            return 0
    except (ProjectAlreadyExists, ProjectNotFound, ValueError) as exc:
        print(f"Error: {exc}")
        return 2

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
