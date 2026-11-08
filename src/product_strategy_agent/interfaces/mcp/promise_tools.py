"""Read-only structural preflight of exact promise text supplied by the IDE agent."""
from product_strategy_agent.domain.capabilities.promises import PromiseCheckRequest
from product_strategy_agent.interfaces.mcp.agent_tools import READ
from product_strategy_agent.interfaces.mcp.errors import invoke


def register_promise_tools(server, services):
    @server.tool(annotations=READ)
    def psa_main_check_promises(project_key: str, request: PromiseCheckRequest) -> dict:
        """Check candidate text and explicit capability/claim links without a model call or writes.

        Uses a consistent project-scoped snapshot. Blocks unavailable capabilities, non-factual/inactive
        or unrelated claims, missing/stale/corrupt sources, unverified locators and invalid quotes.
        eligible_for_human_review means structural checks only: humans must assess semantic fit and limits.
        NEVER authorizes customer promises, publication, workflow gates or automatic approval.
        Returns a hash-bound review packet, not a durable approval or a token to bypass later checks.
        """
        return invoke(lambda: services.promises.check(project_key, request))
