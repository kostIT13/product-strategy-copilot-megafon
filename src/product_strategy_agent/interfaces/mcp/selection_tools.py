"""Explicit human selection; these tools never generate or approve a workflow."""
from uuid import UUID
from product_strategy_agent.domain.decisions.selection import SelectionCommand
from product_strategy_agent.interfaces.mcp.agent_tools import READ
from product_strategy_agent.interfaces.mcp.errors import invoke


def register_selection_tools(server, services):
    @server.tool(annotations=READ)
    def psa_main_preview_selection(project_key: str, source_run_id: UUID, critic_run_id: UUID) -> dict:
        """Read options, critic, pinned hashes and stale-source flags before a HUMAN chooses.

        No state changes or model call. Owner/review fields are self-reported, not authenticated identity.
        """
        return invoke(lambda: services.selection.preview(project_key, source_run_id, critic_run_id))

    @server.tool(annotations={"readOnlyHint": False, "destructiveHint": False,
                              "idempotentHint": True, "openWorldHint": False})
    def psa_main_record_selection(project_key: str, selection: SelectionCommand) -> dict:
        """Only on explicit human instruction: persist three reviewed options and a human decision atomically.

        Require preview hashes, owner, rationale, review note/trigger, all dispositions and confirmed=true.
        Negative critic requires explicit human critic_resolution. Never infer consent from a model verdict.
        Does not create facts/claims or grant workflow approval. Same input replays the immutable receipt.
        """
        return invoke(lambda: services.selection.record(project_key, selection))

    @server.tool(annotations=READ)
    def psa_main_get_selection(project_key: str, source_run_id: UUID) -> dict:
        """Read the immutable human-selection receipt and original review snapshot in this project."""
        return invoke(lambda: services.selection.get(project_key, source_run_id))
