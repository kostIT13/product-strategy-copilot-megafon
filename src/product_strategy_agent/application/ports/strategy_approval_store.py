"""Persist approval only after rechecking the reviewed snapshot in one transaction."""
from typing import Protocol
from uuid import UUID
from product_strategy_agent.domain.decisions.strategy_approval import StrategyApprovalCommand


class StrategyApprovalStore(Protocol):
    def get(self, project_id: UUID, strategy_run_id: UUID) -> dict | None: ...

    def record(self, project_id: UUID, command: StrategyApprovalCommand, request_hash: str, preview: dict) -> dict: ...
