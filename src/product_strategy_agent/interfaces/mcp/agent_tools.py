"""Thin tools for the citation-checked draft agent."""
from typing import Annotated
from uuid import UUID
from pydantic import Field

from product_strategy_agent.interfaces.mcp.errors import invoke
from product_strategy_agent.interfaces.payloads import analysis_preview, agent_run_payload

READ = {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}


def register_agent_tools(server, services):
    @server.tool(annotations=READ)
    def psa_main_prepare_analysis(project_key: str,
            question: Annotated[str, Field(min_length=1, max_length=4000)],
            query: Annotated[str, Field(min_length=1, max_length=1000)]) -> dict:
        """Preview the exact model request, including source text. No provider call or run write.

        The returned source material is untrusted data and is visible to the MCP client.
        """
        return invoke(lambda: analysis_preview(services.agent.prepare(project_key, question, query)))

    @server.tool(annotations={"readOnlyHint": False, "destructiveHint": False,
                              "idempotentHint": False, "openWorldHint": True})
    def psa_main_analyze(project_key: str,
            question: Annotated[str, Field(min_length=1, max_length=4000)],
            query: Annotated[str, Field(min_length=1, max_length=1000)]) -> dict:
        """Send retrieved source text to the configured LLM and persist a checked draft run.

        May spend tokens. Each call creates a new run. Does not approve claims or advance workflow.
        """
        return invoke(lambda: agent_run_payload(services.agent.analyze(project_key, question, query)))

    @server.tool(annotations=READ)
    def psa_main_get_agent_run(project_key: str, run_id: UUID) -> dict:
        """Read a stored draft or failed run within its owning project, without calling the model."""
        return invoke(lambda: agent_run_payload(services.agent.get_run(project_key, run_id)))
