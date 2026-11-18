"""CLI for preparing and checking an authored UX walkthrough."""

import json
from pathlib import Path

from product_strategy_agent.adapters.persistence.files.ux_reader import (
    inspect_ux_review,
    prepare_ux,
)
from product_strategy_agent.domain.projects.ux_review import Journey, UXReview


def add_ux_commands(commands):
    group = commands.add_parser(
        "ux", help="prepare and check a screenshot-based journey"
    )
    actions = group.add_subparsers(dest="ux_command", required=True)
    for name, help_text in (
        ("prepare", "bind journey steps to selected screenshots"),
        ("check", "validate observation regions and screenshot identity"),
    ):
        command = actions.add_parser(name, help=help_text)
        command.add_argument("project_id")
        command.add_argument("--input", type=Path, required=True)
        command.add_argument("--projects-dir", type=Path, default=Path("projects"))


def handle_ux_command(args):
    with args.input.open("rb") as stream:
        data = stream.read(1048577)
    if len(data) > 1048576:
        raise ValueError("UX request exceeds 1 MiB")
    prepare = args.ux_command == "prepare"
    try:
        request = (Journey if prepare else UXReview).model_validate_json(data)
    except ValueError:
        raise ValueError("Invalid UX input. See docs/ux-review.md") from None
    handler = prepare_ux if prepare else inspect_ux_review
    print(
        json.dumps(
            handler(args.projects_dir, args.project_id, request),
            ensure_ascii=True,
            indent=2,
        )
    )
