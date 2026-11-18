"""Check an authored interview analysis with the file research workflow."""

import json
from pathlib import Path

from product_strategy_agent.adapters.persistence.files.interview_reader import (
    interview_report,
)
from product_strategy_agent.domain.projects.interview_analysis import InterviewAnalysis
from product_strategy_agent.domain.projects.model_respondent import (
    RespondentBrief,
    RespondentCapture,
    prepare_respondent,
    export_respondent,
)


def add_interview_commands(commands):
    group = commands.add_parser("interview", help="check analysis of local transcripts")
    actions = group.add_subparsers(dest="interview_command", required=True)
    check = actions.add_parser(
        "check",
        help="verify coded evidence in an authored interview draft",
    )
    check.add_argument("project_id")
    check.add_argument("--input", type=Path, required=True)
    check.add_argument("--projects-dir", type=Path, default=Path("projects"))
    prepare = actions.add_parser(
        "prepare-respondent", help="build a fictional respondent brief for the IDE"
    )
    prepare.add_argument("--input", type=Path, required=True)
    export = actions.add_parser(
        "export-respondent",
        help="render a marked transcript from an authored role-play",
    )
    export.add_argument("--input", type=Path, required=True)


def handle_interview_command(args):
    with args.input.open("rb") as stream:
        data = stream.read(1048577)
    if len(data) > 1048576:
        raise ValueError("Interview request exceeds 1 MiB")
    models = {
        "check": InterviewAnalysis,
        "prepare-respondent": RespondentBrief,
        "export-respondent": RespondentCapture,
    }
    command = args.interview_command
    try:
        request = models[command].model_validate_json(data)
    except ValueError:
        raise ValueError(
            "Invalid interview input. See docs/interview-analysis.md and docs/model-respondent.md"
        ) from None
    if command == "check":
        result = interview_report(args.projects_dir, args.project_id, request)
    elif command == "prepare-respondent":
        result = prepare_respondent(request)
    else:
        result = export_respondent(request)
    print(json.dumps(result, ensure_ascii=True, indent=2))
