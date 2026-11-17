"""Read one bounded usage ledger under the canonical case boundary."""

from typing import Protocol
from product_strategy_agent.domain.automation.usage_provenance import UsageSnapshot


class UsageProvenanceReader(Protocol):
    def read(self, project_id: str) -> UsageSnapshot: ...
