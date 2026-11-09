"""Direct structured IDE input and explicit file-journal status/recovery."""
import json
from pathlib import Path
from uuid import UUID
from product_strategy_agent.application.services.research_artifact_service import ResearchArtifactService
from product_strategy_agent.adapters.persistence.files.research_artifact_repository import FileResearchArtifactStore
from product_strategy_agent.domain.projects.research_artifact import RecordResearchArtifact


def add_research_artifact_commands(commands):
    parser = commands.add_parser("artifact", help="Versioned research-plan drafts, without model or gate approval")
    actions = parser.add_subparsers(dest="artifact_action", required=True)
    for name in ("status", "record", "show", "pending", "recover"):
        command = actions.add_parser(name)
        command.add_argument("project_id")
        command.add_argument("--projects-dir", type=Path, default=Path("projects"))
        if name == "record":
            command.add_argument("--input", type=Path, required=True)
        if name in {"show", "recover"}:
            command.add_argument("--operation", type=UUID, required=name == "recover")


def handle_research_artifact_command(args):
    service = ResearchArtifactService(FileResearchArtifactStore(args.projects_dir))
    if args.artifact_action == "record":
        with args.input.open("rb") as stream:
            data = stream.read(128001)
        if len(data) > 128000:
            raise ValueError("artifact request exceeds 128000 bytes")
        try:
            command = RecordResearchArtifact.model_validate_json(data)
        except ValueError:
            raise ValueError("invalid research artifact input; check required fields/types/limits") from None
        result = service.record(args.project_id, command)
    elif args.artifact_action in {"show", "recover"}:
        result = getattr(service, args.artifact_action)(args.project_id, args.operation)
    else:
        result = getattr(service, args.artifact_action)(args.project_id)
    print(json.dumps(result, ensure_ascii=True, indent=2))
