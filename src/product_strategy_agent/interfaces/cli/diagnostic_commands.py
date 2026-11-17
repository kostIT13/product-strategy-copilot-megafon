"""One text-free diagnostic for a selected historical operation."""

import json
from pathlib import Path
from typing import get_args
from uuid import UUID
from product_strategy_agent.interfaces.usage_provenance import usage_provenance
from product_strategy_agent.domain.automation.operation_diagnostics import (
    DiagnoseOperation,
    OperationKind,
)
from product_strategy_agent.interfaces.operation_diagnostics import (
    operation_diagnostics,
)
from product_strategy_agent.domain.automation.operation_summary import (
    parse_summary,
    SUMMARY_LIMIT,
)


def add_diagnostic_commands(commands):
    parser = commands.add_parser(
        "diagnostics", help="inspect recorded automation metadata without execution"
    )
    actions = parser.add_subparsers(dest="diagnostic_action", required=True)
    for name in ("operation", "controls"):
        operation = actions.add_parser(name)
        operation.add_argument("project_id")
        operation.add_argument("operation_id", type=UUID)
        operation.add_argument("--kind", choices=get_args(OperationKind), required=True)
        operation.add_argument("--projects-dir", type=Path, default=Path("projects"))
    summary = actions.add_parser("summary")
    summary.add_argument("--request", type=Path, required=True)
    summary.add_argument("--projects-dir", type=Path, default=Path("projects"))
    usage = actions.add_parser("usage")
    usage.add_argument("project_id")
    usage.add_argument("--projects-dir", type=Path, default=Path("projects"))


def handle_diagnostic_command(args):
    if args.diagnostic_action == "usage":
        result = usage_provenance(args.projects_dir).inspect(args.project_id)
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return
    if args.diagnostic_action == "summary":
        with args.request.open("rb") as stream:
            request = parse_summary(stream.read(SUMMARY_LIMIT + 1))
        result = operation_diagnostics(args.projects_dir).summary(request)
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return
    request = DiagnoseOperation(
        project_id=args.project_id, operation_id=args.operation_id, kind=args.kind
    )
    service = operation_diagnostics(args.projects_dir)
    result = (
        service.controls(request)
        if args.diagnostic_action == "controls"
        else service.inspect(request)
    )
    print(json.dumps(result, ensure_ascii=True, indent=2))
