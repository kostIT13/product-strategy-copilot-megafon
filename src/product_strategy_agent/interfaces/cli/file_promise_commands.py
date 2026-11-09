"""Check draft commitments without publication or implicit workflow consent."""

import json
from pathlib import Path
from product_strategy_agent.adapters.persistence.files.promise_reader import (
    FilePromiseReader,
)
from product_strategy_agent.application.services.file_promise_service import (
    FilePromiseService,
)


def add_file_promise_commands(commands):
    parser = commands.add_parser(
        "promise", help="check draft promises against current file evidence"
    )
    check = parser.add_subparsers(dest="promise_action", required=True).add_parser(
        "check"
    )
    check.add_argument("project_id")
    check.add_argument("--projects-dir", type=Path, default=Path("projects"))


def handle_file_promise_command(args):
    result = FilePromiseService(FilePromiseReader(args.projects_dir)).check(
        args.project_id
    )
    print(json.dumps(result, ensure_ascii=True, indent=2))
    if result["structural_status"] == "blocked":
        raise SystemExit(3)
