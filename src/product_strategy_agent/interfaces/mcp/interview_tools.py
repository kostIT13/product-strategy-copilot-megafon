"""Validate a selected transcript analysis locally."""

from product_strategy_agent.adapters.persistence.files.interview_reader import (
    interview_report,
)
from product_strategy_agent.domain.projects.interview_analysis import InterviewAnalysis


def register_interview_tools(server):
    from fastmcp.exceptions import ToolError

    @server.tool(
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        }
    )
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
