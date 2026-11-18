"""Thin local interfaces; assessment attribution is not authentication or consent."""

from product_strategy_agent.adapters.persistence.files.workflow_repository import (
    FileWorkflowStore,
)
from product_strategy_agent.application.services.source_assessment_service import (
    SourceAssessmentService,
)
from product_strategy_agent.domain.projects.source_assessment import SourceAssessment
from product_strategy_agent.application.services.source_quality_service import (
    inspect_source_quality,
)


def register_source_assessment_tools(server):
    from fastmcp.exceptions import ToolError

    read = {
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }

    @server.tool(annotations=read)
    def psa_source_quality(project_id: str, projects_dir: str = "projects") -> dict:
        """Report source assessment gaps and invalidations for active evidence."""
        try:
            return inspect_source_quality(FileWorkflowStore(projects_dir), project_id)
        except (ValueError, OSError):
            raise ToolError(
                "Source quality summary unavailable. Check case integrity and pending operations."
            ) from None

    @server.tool(annotations=read)
    def psa_source_assessment(
        project_id: str, source_id: str, projects_dir: str = "projects"
    ) -> dict:
        """Inspect current hash/version and recorded source assessment. No fetch/write/approval."""
        try:
            return SourceAssessmentService(FileWorkflowStore(projects_dir)).inspect(
                project_id, source_id
            )
        except (ValueError, OSError):
            raise ToolError(
                "source assessment unavailable; inspect case integrity, lock and pending operations"
            ) from None

    @server.tool(annotations={**read, "readOnlyHint": False})
    def psa_assess_source(
        project_id: str, request: SourceAssessment, projects_dir: str = "projects"
    ) -> dict:
        """Record source author/owner/date/reliability/basis/limitations, pinned to current hash and version.
        Metadata is self-reported, never independent verification, a factual claim or gate approval.
        Exact UUID replay never reapplies historical metadata. No source acquisition/model.
        """
        try:
            return SourceAssessmentService(FileWorkflowStore(projects_dir)).record(
                project_id, request
            )
        except ValueError:
            raise ToolError(
                "source assessment refused; inspect request fields and current source snapshot"
            ) from None
        except OSError:
            raise ToolError(
                "source assessment files unavailable; inspect workflow pending before retrying"
            ) from None
