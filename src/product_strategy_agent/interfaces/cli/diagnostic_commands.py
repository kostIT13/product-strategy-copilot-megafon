"""One text-free diagnostic for a selected historical operation."""

import json
from pathlib import Path
from typing import get_args
from uuid import UUID
from product_strategy_agent.domain.automation.operation_diagnostics import (
    DiagnoseOperation,
    OperationKind,
)
from product_strategy_agent.interfaces.operation_diagnostics import (
    operation_diagnostics,
)


def add_diagnostic_commands(commands):
    parser = commands.add_parser(
        "diagnostics", help="inspect recorded automation metadata without execution"
    )
    actions = parser.add_subparsers(dest="diagnostic_action", required=True)
    operation = actions.add_parser("operation")
    operation.add_argument("project_id")
    operation.add_argument("operation_id", type=UUID)
    operation.add_argument("--kind", choices=get_args(OperationKind), required=True)
    operation.add_argument("--projects-dir", type=Path, default=Path("projects"))


def handle_diagnostic_command(args):
    request = DiagnoseOperation(
        project_id=args.project_id, operation_id=args.operation_id, kind=args.kind
    )
    result = operation_diagnostics(args.projects_dir).inspect(request)
    print(json.dumps(result, ensure_ascii=True, indent=2))
