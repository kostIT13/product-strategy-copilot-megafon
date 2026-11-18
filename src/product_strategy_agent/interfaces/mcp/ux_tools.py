"""Read-only MCP interfaces for the screenshot walkthrough."""

from product_strategy_agent.adapters.persistence.files.ux_reader import (
    inspect_ux_review,
    prepare_ux,
)
from product_strategy_agent.domain.projects.ux_review import Journey, UXReview


def register_ux_tools(server):
    from fastmcp.exceptions import ToolError

    read = {
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }

    @server.tool(annotations=read)
    def psa_ux_prepare(
        project_id: str, journey: Journey, projects_dir: str = "projects"
    ) -> dict:
        """Bind the selected journey and PNG screenshots to a local manifest."""
        try:
            return prepare_ux(projects_dir, project_id, journey)
        except (ValueError, OSError):
            raise ToolError(
                "UX journey refused. Check the case and selected PNG screenshots."
            ) from None

    @server.tool(annotations=read)
    def psa_ux_check(
        project_id: str, review: UXReview, projects_dir: str = "projects"
    ) -> dict:
        """Check authored findings against the current screenshot manifest and pixel regions."""
        try:
            return inspect_ux_review(projects_dir, project_id, review)
        except (ValueError, OSError):
            raise ToolError(
                "UX review refused. Check the screenshot manifest and observation regions."
            ) from None
