"""Explicit append-only withdrawal publication and read-only effective impact."""

from contextlib import AbstractContextManager
from typing import Protocol
from product_strategy_agent.domain.projects.claim_lifecycle import ClaimWithdrawal


class ClaimLifecycleStore(Protocol):
    def access(self, project_id: str) -> AbstractContextManager: ...
    def replay(self, project_id: str, command: ClaimWithdrawal) -> dict | None: ...
    def capture_claims(self, project_id: str) -> dict: ...
    def inspect_claims(self, project_id: str) -> dict: ...
    def commit(
        self,
        project_id,
        command,
        before_state,
        after_state,
        before_events,
        event,
        inputs,
    ) -> dict: ...
