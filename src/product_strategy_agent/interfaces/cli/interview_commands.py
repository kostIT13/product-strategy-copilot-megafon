"""Check an authored interview analysis with the file research workflow."""

import json
from pathlib import Path

from product_strategy_agent.adapters.persistence.files.interview_reader import (
    interview_report,
)
from product_strategy_agent.domain.projects.interview_analysis import InterviewAnalysis


def add_interview_commands(commands):
    group = commands.add_parser("interview", help="check analysis of local transcripts")
    check = group.add_subparsers(dest="interview_command", required=True).add_parser(
        "check",
        help="verify coded evidence in an authored interview draft",
    )
    check.add_argument("project_id")
    check.add_argument("--input", type=Path, required=True)
    check.add_argument("--projects-dir", type=Path, default=Path("projects"))


def handle_interview_command(args):
    with args.input.open("rb") as stream:
        data = stream.read(1048577)
    if len(data) > 1048576:
        raise ValueError("Interview request exceeds 1 MiB")
    try:
        request = InterviewAnalysis.model_validate_json(data)
    except ValueError:
        raise ValueError(
            "Invalid interview draft. Check the schema in docs/interview-analysis.md"
        ) from None
    result = interview_report(args.projects_dir, args.project_id, request)
    print(json.dumps(result, ensure_ascii=True, indent=2))
