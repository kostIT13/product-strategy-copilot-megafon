"""Inspect an authored measurement plan without executing an experiment."""

import json
from pathlib import Path
from product_strategy_agent.adapters.persistence.files.validation_plan_store import (
    FileValidationPlanStore,
)
from product_strategy_agent.application.services.validation_plan_service import (
    ValidationPlanService,
)
from product_strategy_agent.application.services.baseline_numbers_service import (
    BaselineNumbersService,
)


def add_validation_plan_commands(commands):
    parser = commands.add_parser(
        "validation", help="check metrics baseline window and guardrails"
    )
    actions = parser.add_subparsers(dest="validation_action", required=True)
    for name in ("check", "numbers"):
        check = actions.add_parser(name)
        check.add_argument("project_id")
        check.add_argument("--projects-dir", type=Path, default=Path("projects"))


def handle_validation_plan_command(args):
    if args.validation_action == "numbers":
        report = BaselineNumbersService(
            FileValidationPlanStore(args.projects_dir)
        ).check(args.project_id)
        print(json.dumps(report, ensure_ascii=True, indent=2))
        if report["status"] == "blocked":
            raise SystemExit(3)
        return
    report = ValidationPlanService(FileValidationPlanStore(args.projects_dir)).check(
        args.project_id
    )
    print(json.dumps(report, ensure_ascii=True, indent=2))
    if report["structural_status"] != "complete":
        raise SystemExit(3)
