"""Planning preview and checkpoint creation, with no implicit model execution."""
from dataclasses import asdict
from uuid import UUID
from product_strategy_agent.interfaces.mcp.agent_tools import READ
from product_strategy_agent.interfaces.mcp.errors import invoke
from product_strategy_agent.interfaces.payloads import analysis_preview, json_payload


def register_strategy_tools(server, services):
    @server.tool(annotations=READ)
    def psa_main_prepare_strategy(project_key: str, source_run_id: UUID, question: str) -> dict:
        """Preview an internal strategy request for recorded human selection; no writes/model call.

        Includes decision, owner notes, original evidence and critic context for the MCP client.
        Communication drafts are hypotheses; no customer commitments or publication approval.
        """
        return invoke(lambda: analysis_preview(services.strategy.prepare(project_key, source_run_id, question)))

    @server.tool(annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": False})
    def psa_main_start_strategy(project_key: str, source_run_id: UUID, question: str) -> dict:
        """Pin recorded decision/selection and evidence for a strategy pipeline without calling the model.

        Resume via resume_pipeline explicitly; that generation may spend tokens. Results require human review.
        Does not approve publication, change decisions, create claims or advance the human workflow.
        """
        return invoke(lambda: json_payload(asdict(services.strategy.start(project_key, source_run_id, question))))
