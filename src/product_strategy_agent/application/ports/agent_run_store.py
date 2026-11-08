"""Persistent agent checkpoints and terminal draft results."""
from typing import Protocol
from uuid import UUID
from product_strategy_agent.domain.agent.models import AgentRun


class AgentRunStore(Protocol):
    def create(self, run: AgentRun) -> AgentRun: ...

    def finish(self, run_id: UUID, status: str, *, result: dict | None = None,
               usage: dict | None = None, error_code: str | None = None) -> AgentRun: ...

    def get(self, project_id: UUID, run_id: UUID) -> AgentRun | None: ...
