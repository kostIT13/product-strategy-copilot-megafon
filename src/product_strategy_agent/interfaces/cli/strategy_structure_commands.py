"""Inspect required strategy sections without writing drafts or consent."""

import json
from pathlib import Path
from product_strategy_agent.adapters.persistence.files.strategy_structure_reader import (
    FileStrategyStructureReader,
)
from product_strategy_agent.application.services.strategy_structure_service import (
    StrategyStructureService,
)


def add_strategy_structure_commands(commands):
    parser = commands.add_parser(
        "strategy", help="check structural completeness of author strategy drafts"
    )
    check = parser.add_subparsers(dest="strategy_action", required=True).add_parser(
        "check"
    )
    check.add_argument("project_id")
    check.add_argument("--projects-dir", type=Path, default=Path("projects"))


def handle_strategy_structure_command(args):
    report = StrategyStructureService(
        FileStrategyStructureReader(args.projects_dir)
    ).check(args.project_id)
    print(json.dumps(report, ensure_ascii=True, indent=2))
    if report["structural_status"] != "complete":
        raise SystemExit(3)
