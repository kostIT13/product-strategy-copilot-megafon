"""Read shipped declarations only; never probe files, extras, hosts or providers."""

from product_strategy_agent.domain.research.shipped_tools import TOOLS
from product_strategy_agent.domain.research.tool_registry import (
    DiscoverTools,
    ResearchRegistry,
)


class ResearchToolRegistryService:
    def describe(self, tool_id: str | None = None) -> dict:
        try:
            request = DiscoverTools(tool_id=tool_id)
        except ValueError:
            raise ValueError("unknown research tool ID; use psa tools list") from None
        selected = tuple(
            tool
            for tool in TOOLS
            if request.tool_id is None or tool.tool_id == request.tool_id
        )
        return ResearchRegistry(tools=selected).model_dump(mode="json")
