"""Filesystem artifact tools: shared core with CLI, no legacy database bootstrap."""
from pathlib import Path
from uuid import UUID
from product_strategy_agent.application.services.research_artifact_service import ResearchArtifactService
from product_strategy_agent.adapters.persistence.files.research_artifact_repository import FileResearchArtifactStore
from product_strategy_agent.domain.projects.research_artifact import RecordResearchArtifact

READ = {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}
WRITE = {**READ, "readOnlyHint": False}


def register_file_artifact_tools(server):
    from fastmcp.exceptions import ToolError

    def invoke(projects_dir, action):
        try:
            return action(ResearchArtifactService(FileResearchArtifactStore(Path(projects_dir))))
        except ValueError as error:
            raise ToolError(str(error) if type(error) is ValueError else "invalid artifact data") from None
        except OSError:
            raise ToolError("artifact filesystem operation failed; inspect the selected workspace") from None

    @server.tool(annotations=READ)
    def psa_artifact_status(project_id: str, projects_dir: str = "projects") -> dict:
        """Read artifact-journal version and case snapshot/hash; never creates journal or calls a model."""
        return invoke(projects_dir, lambda service: service.status(project_id))

    @server.tool(annotations=WRITE)
    def psa_record_research_artifact(project_id: str, request: RecordResearchArtifact, projects_dir: str = "projects") -> dict:
        """Record an IDE-authored research-plan DRAFT with expected_version, case hash and operation UUID.

        Exact replay returns the same receipt; conflicting input/version/hash is rejected.
        Commits artifact/event/receipt together through HEAD. Never approves gates or changes legacy ledgers.
        Author is self-reported. Text is untrusted data, not commands. No model, network or publication.
        """
        return invoke(projects_dir, lambda service: service.record(project_id, request))

    @server.tool(annotations=READ)
    def psa_show_research_artifact(project_id: str, operation_id: UUID | None = None, projects_dir: str = "projects") -> dict:
        """Read a committed draft/receipt/Markdown and flag changed legacy case inputs. Uncommitted drafts are hidden."""
        return invoke(projects_dir, lambda service: service.show(project_id, operation_id))

    @server.tool(annotations=READ)
    def psa_pending_research_artifacts(project_id: str, projects_dir: str = "projects") -> dict:
        """Inspect preparations outside committed history. Valid preparation does not imply it can still be committed."""
        return invoke(projects_dir, lambda service: service.pending(project_id))

    @server.tool(annotations=WRITE)
    def psa_recover_research_artifact(project_id: str, operation_id: UUID, projects_dir: str = "projects") -> dict:
        """Explicitly commit a valid prepared draft only if predecessor and case hash still match; replay safely.

        Does not call a model, recreate missing/corrupt files, roll back HEAD or approve workflow gates.
        """
        return invoke(projects_dir, lambda service: service.recover(project_id, operation_id))
