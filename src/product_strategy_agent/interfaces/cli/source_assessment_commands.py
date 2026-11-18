"""Explicit source metadata assessment, not a factual claim or human gate."""

import json
from pathlib import Path

from product_strategy_agent.adapters.persistence.files.workflow_repository import (
    FileWorkflowStore,
)
from product_strategy_agent.application.services.source_assessment_service import (
    SourceAssessmentService,
)
from product_strategy_agent.domain.projects.source_assessment import SourceAssessment


def add_source_assessment_commands(commands):
    inspect = commands.add_parser(
        "assessment", help="inspect current source/hash/version and recorded assessment"
    )
    assess = commands.add_parser(
        "assess",
        help="record an attributed assessment against the current source snapshot",
    )
    for parser in (inspect, assess):
        parser.add_argument("project_id")
        parser.add_argument("--projects-dir", type=Path, default=Path("projects"))
    inspect.add_argument("source_id")
    assess.add_argument("--input", type=Path, required=True)


def handle_source_assessment_command(args):
    service = SourceAssessmentService(FileWorkflowStore(args.projects_dir))
    if args.source_command == "assessment":
        result = service.inspect(args.project_id, args.source_id)
    else:
        with args.input.open("rb") as stream:
            data = stream.read(16385)
        if len(data) > 16384:
            raise ValueError("source assessment input exceeds 16384 bytes")
        try:
            command = SourceAssessment.model_validate_json(data)
        except ValueError:
            raise ValueError(
                "invalid source assessment fields; check types, date and unknowns"
            ) from None
        result = service.record(args.project_id, command)
    print(json.dumps(result, ensure_ascii=True, indent=2))
