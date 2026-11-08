"""Read only the requested project evidence from a consistent database snapshot."""
from typing import Protocol
from product_strategy_agent.domain.capabilities.promises import PromiseCheckRequest, PromiseEvidenceSnapshot


class PromiseEvidenceReader(Protocol):
    def read(self, project_key: str, request: PromiseCheckRequest) -> PromiseEvidenceSnapshot: ...
