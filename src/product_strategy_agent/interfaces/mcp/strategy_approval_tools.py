"""Human internal acceptance and read-only export; no publication authority."""
from uuid import UUID
from product_strategy_agent.domain.decisions.strategy_approval import StrategyApprovalCommand
from product_strategy_agent.interfaces.mcp.agent_tools import READ
from product_strategy_agent.interfaces.mcp.errors import invoke


def register_strategy_approval_tools(server, services):
    @server.tool(annotations=READ)
    def psa_main_preview_strategy_approval(project_key: str, strategy_run_id: UUID, critic_run_id: UUID) -> dict:
        """Read the pinned strategy, linked critic and approval hash for explicit HUMAN review.

        No model call or writes. Stale sources block acceptance. This preview is not consent.
        """
        return invoke(lambda: services.strategy_approval.preview(project_key, strategy_run_id, critic_run_id))

    @server.tool(annotations={"readOnlyHint": False, "destructiveHint": False,
                              "idempotentHint": True, "openWorldHint": False})
    def psa_main_approve_strategy(project_key: str, approval: StrategyApprovalCommand) -> dict:
        """Only on explicit HUMAN instruction: record internal_review acceptance of the exact preview.

        Require confirmed=true, owner, review_note and explicit resolution of critic concerns.
        Owner is self-reported, not authenticated. Never infer consent from a critic or model verdict.
        Does not authorize publication, customer promises or workflow gates. Same command replays the receipt.
        """
        return invoke(lambda: services.strategy_approval.record(project_key, approval))

    @server.tool(annotations=READ)
    def psa_main_get_strategy_approval(project_key: str, strategy_run_id: UUID) -> dict:
        """Read a historical immutable approval receipt; use export to recheck current input freshness."""
        return invoke(lambda: services.strategy_approval.get(project_key, strategy_run_id))

    @server.tool(annotations=READ)
    def psa_main_export_strategy(project_key: str, strategy_run_id: UUID) -> dict:
        """Return internal Markdown/JSON file contents and SHA-256 after checking approval and freshness.

        Does not write host files, publish, call a model or turn hypotheses into customer promises.
        The caller can save the returned files; stale or changed approved inputs are rejected.
        """
        return invoke(lambda: services.strategy_approval.export(project_key, strategy_run_id))
