"""JSON input for reproducible table selection and aggregate requests."""

import json
from pathlib import Path

from product_strategy_agent.adapters.persistence.files.table_reader import table_report
from product_strategy_agent.domain.projects.table_analysis import TableRequest


def add_table_commands(commands):
    command = commands.add_parser(
        "table",
        help="profile an imported CSV or XLSX and optionally calculate aggregates",
    )
    command.add_argument("project_id")
    command.add_argument("--input", type=Path, required=True)
    command.add_argument("--projects-dir", type=Path, default=Path("projects"))


def handle_table_command(args):
    with args.input.open("rb") as stream:
        data = stream.read(32769)
    if len(data) > 32768:
        raise ValueError("Table analysis request exceeds 32 KiB")
    try:
        request = TableRequest.model_validate_json(data)
    except ValueError:
        raise ValueError(
            "Invalid table request. Check the schema in docs/table-analysis.md"
        ) from None
    print(
        json.dumps(
            table_report(args.projects_dir, args.project_id, request),
            ensure_ascii=True,
            indent=2,
        )
    )
