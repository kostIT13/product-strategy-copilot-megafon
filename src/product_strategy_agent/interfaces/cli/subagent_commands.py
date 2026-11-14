"""Read-only explicit preparation; output to stdout, no agent dispatch or task journal."""

import json
from pathlib import Path
from product_strategy_agent.adapters.persistence.files.handoff_reader import (
    FileHandoffReader,
)
from product_strategy_agent.adapters.persistence.files.role_instruction_reader import (
    FileRoleInstructionReader,
)
from product_strategy_agent.application.services.handoff_service import HandoffService
from product_strategy_agent.domain.automation.handoffs import parse_request


def add_subagent_commands(commands):
    parser = commands.add_parser(
        "subagent", help="prepare bounded read-only role handoffs; no execution"
    )
    action = parser.add_subparsers(dest="subagent_action", required=True).add_parser(
        "prepare"
    )
    action.add_argument("project_id")
    action.add_argument("--request", type=Path, required=True)
    action.add_argument("--projects-dir", type=Path, default=Path("projects"))
    action.add_argument("--instructions-root", type=Path, default=Path("."))


def handle_subagent_command(args):
    with args.request.open("rb") as stream:
        raw = stream.read(64001)
    if len(raw) > 64000:
        raise ValueError("handoff request exceeds 64000 bytes")
    request = parse_request(raw)
    result = HandoffService(
        FileHandoffReader(args.projects_dir),
        FileRoleInstructionReader(args.instructions_root),
    ).prepare(args.project_id, request)
    print(json.dumps(result, ensure_ascii=True, indent=2))
