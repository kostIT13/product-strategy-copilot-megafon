"""Author-supplied correction JSON and explicit attribution; never rewrite original claims."""

import json
from pathlib import Path
from uuid import UUID, uuid4
from pydantic import ValidationError
from product_strategy_agent.adapters.persistence.files.workflow_repository import (
    FileWorkflowStore,
)
from product_strategy_agent.application.services.claim_correction_service import (
    ClaimCorrectionService,
)
from product_strategy_agent.domain.projects.claim_correction import ClaimCorrection
from product_strategy_agent.domain.projects.validation_plan import unique_object


def add_claim_correction_command(commands):
    parser = commands.add_parser(
        "correct", help="append an attributed replacement with current citation checks"
    )
    parser.add_argument("project_id")
    parser.add_argument("claim_id")
    parser.add_argument(
        "--replacement",
        type=Path,
        required=True,
        help="JSON ClaimPayload; original claim remains immutable",
    )
    parser.add_argument("--by", required=True)
    parser.add_argument("--reason", required=True)
    parser.add_argument("--operation", type=UUID)
    parser.add_argument("--expected-workflow-version", type=int)
    parser.add_argument("--projects-dir", type=Path, default=Path("projects"))


def handle_claim_correction_command(args):
    with args.replacement.open("rb") as stream:
        raw = stream.read(64001)
    if len(raw) > 64000:
        raise ValueError("correction input exceeds 64000 bytes")
    try:
        body = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=unique_object)
        command = ClaimCorrection(
            operation_id=args.operation or uuid4(),
            claim_id=args.claim_id,
            corrected_by=args.by,
            reason=args.reason,
            replacement=body,
            expected_workflow_version=args.expected_workflow_version,
        )
    except ValidationError as error:
        raise ValueError(
            "invalid correction fields: "
            + ", ".join(
                ".".join(map(str, row["loc"]))
                for row in error.errors(include_input=False)
            )
        ) from None
    except RecursionError:
        raise ValueError("correction JSON nesting exceeds the parser limit") from None
    result = ClaimCorrectionService(FileWorkflowStore(args.projects_dir)).correct(
        args.project_id, command
    )
    print(json.dumps(result, ensure_ascii=True, indent=2))
