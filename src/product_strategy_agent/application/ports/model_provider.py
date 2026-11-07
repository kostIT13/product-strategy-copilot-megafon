"""Port for one bounded model completion without tool execution."""
from typing import Protocol
from product_strategy_agent.domain.agent.models import ModelReply


class ModelProvider(Protocol):
    model: str

    def generate(self, messages: list[dict[str, str]]) -> ModelReply: ...
