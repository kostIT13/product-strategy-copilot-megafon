"""Validate a selected transcript analysis locally."""

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


def register_interview_tools(server):
    from fastmcp.exceptions import ToolError

    read_local = {
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }

    @server.tool(annotations=read_local)
    def psa_prepare_respondent(brief: RespondentBrief) -> dict:
        """Build a bounded, fictional role-play brief for the caller's IDE."""
        return prepare_respondent(brief)

    @server.tool(annotations=read_local)
    def psa_export_respondent(capture: RespondentCapture) -> dict:
        """Render a marked synthetic transcript and hypotheses from an authored role-play."""
        return export_respondent(capture)

    @server.tool(annotations=read_local)
    def psa_interview_check(
        project_id: str, request: InterviewAnalysis, projects_dir: str = "projects"
    ) -> dict:
        """Verify exact transcript quotes and report authored themes with explicit evidence scope."""
        try:
            return interview_report(projects_dir, project_id, request)
        except (ValueError, OSError):
            raise ToolError(
                "Interview draft refused. Check selected sources, revision hashes and quotes."
            ) from None
