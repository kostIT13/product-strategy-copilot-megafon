"""Capability declarations are data; registry discovery never dispatches tools."""

from product_strategy_agent.application.services.research_tool_registry_service import (
    ResearchToolRegistryService,
)


def register_research_tool_registry(server):
    from fastmcp.exceptions import ToolError

    @server.tool(
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        }
    )
    def psa_research_tools(tool_id: str | None = None) -> dict:
        """Describe shipped research tools, permissions/limits/offline fallback. No case access,
        availability probe, network, model, dispatch, permission grant or workflow approval.
        Omit tool_id for all declarations; unknown IDs are refused.
        """
        try:
            return ResearchToolRegistryService().describe(tool_id)
        except ValueError:
            raise ToolError("unknown research tool ID; use psa tools list") from None
