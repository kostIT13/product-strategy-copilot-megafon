"""Explicit source notice preparation; existing bounded run tools execute it."""

from uuid import UUID
from product_strategy_agent.interfaces.source_notification import source_notification


def register_source_notification_tools(server):
    from fastmcp.exceptions import ToolError

    @server.tool(
        annotations=dict(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        )
    )
    def psa_prepare_source_notification(
        project_id: str, operation_id: UUID, projects_dir: str = "projects"
    ) -> dict:
        """Explicitly bind a local source_revision notice to the current case snapshot.

        Use psa_run_hook for bounded execution and journal. Notification failure does not roll back an
        already committed import. Delivery never counts as human review or required gate pass.
        No auto activation, external message, model, source fetch or review resolution.
        """
        try:
            return source_notification(projects_dir).prepare(project_id, operation_id)
        except (ValueError, OSError):
            raise ToolError(
                "source notification unavailable; inspect case readiness and revisit list"
            ) from None
