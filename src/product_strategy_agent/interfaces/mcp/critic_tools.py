"""Critic preparation and reservation; paid execution uses pipeline resume."""
from dataclasses import asdict
from uuid import UUID
from product_strategy_agent.interfaces.mcp.agent_tools import READ
from product_strategy_agent.interfaces.mcp.errors import invoke
from product_strategy_agent.interfaces.payloads import analysis_preview, json_payload


def register_critic_tools(server, services):
    @server.tool(annotations=READ)
    def psa_main_prepare_critic(project_key: str, run_id: UUID) -> dict:
        """Preview an advisory critic request for a successful saved draft and its original sources.

        Returns full source/draft text to the MCP client. No provider call or state write.
        """
        return invoke(lambda: analysis_preview(services.critic.prepare(project_key, run_id)))

    @server.tool(annotations={"readOnlyHint": False, "destructiveHint": False,
                              "idempotentHint": False, "openWorldHint": False})
    def psa_main_start_critic(project_key: str, run_id: UUID) -> dict:
        """Pin a saved draft and source revisions in a new critic pipeline without calling the LLM.

        Execute via resume_pipeline. Critic is advisory; it never approves or rewrites the original.
        """
        return invoke(lambda: json_payload(asdict(services.critic.start(project_key, run_id))))
