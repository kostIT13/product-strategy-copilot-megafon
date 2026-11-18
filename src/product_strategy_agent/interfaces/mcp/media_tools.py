"""Expose local media metadata and observation checks through optional MCP."""

from product_strategy_agent.adapters.persistence.files.media_reader import (
    inspect_media_review,
    prepare_media,
)
from product_strategy_agent.domain.projects.media_review import (
    MediaReview,
    MediaSelection,
)


def register_media_tools(server):
    from fastmcp.exceptions import ToolError

    read = {
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }

    @server.tool(annotations=read)
    def psa_media_prepare(
        project_id: str, selection: MediaSelection, projects_dir: str = "projects"
    ) -> dict:
        """Read local media metadata and SHA-256 for an explicitly selected file."""
        try:
            return prepare_media(projects_dir, project_id, selection)
        except (ValueError, OSError):
            raise ToolError(
                "Media selection refused. Check supported format and case-relative path."
            ) from None

    @server.tool(annotations=read)
    def psa_media_check(
        project_id: str, review: MediaReview, projects_dir: str = "projects"
    ) -> dict:
        """Validate authored observations against the selected media and its bounds."""
        try:
            return inspect_media_review(projects_dir, project_id, review)
        except (ValueError, OSError):
            raise ToolError(
                "Media review refused. Check file identity and observation bounds."
            ) from None
