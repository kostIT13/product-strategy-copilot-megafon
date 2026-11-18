"""Prepare and check local media evidence from authored JSON."""

import json
from pathlib import Path

from product_strategy_agent.adapters.persistence.files.media_reader import (
    inspect_media_review,
    prepare_media,
)
from product_strategy_agent.domain.projects.media_review import (
    MediaReview,
    MediaSelection,
)


def add_media_commands(commands):
    group = commands.add_parser(
        "media", help="prepare and check local media observations"
    )
    actions = group.add_subparsers(dest="media_command", required=True)
    for name in ("prepare", "check"):
        command = actions.add_parser(name)
        command.add_argument("project_id")
        command.add_argument("--input", type=Path, required=True)
        command.add_argument("--projects-dir", type=Path, default=Path("projects"))


def handle_media_command(args):
    with args.input.open("rb") as stream:
        data = stream.read(1048577)
    if len(data) > 1048576:
        raise ValueError("Media request exceeds 1 MiB")
    prepare = args.media_command == "prepare"
    try:
        request = (MediaSelection if prepare else MediaReview).model_validate_json(data)
    except ValueError:
        raise ValueError("Invalid media input. See docs/media-review.md") from None
    handler = prepare_media if prepare else inspect_media_review
    print(
        json.dumps(
            handler(args.projects_dir, args.project_id, request),
            ensure_ascii=True,
            indent=2,
        )
    )
