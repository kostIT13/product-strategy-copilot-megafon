"""Transactional checkpoints with project-scoped reads and terminal-state guards."""
from dataclasses import asdict
from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy import select
from product_strategy_agent.adapters.persistence.postgres.database import get_session_factory
from product_strategy_agent.adapters.persistence.postgres.models import AgentRunRecord
from product_strategy_agent.domain.agent.models import AgentRun


class PostgresAgentRunStore:
    def create(self, run: AgentRun) -> AgentRun:
        if run.status != "running":
            raise ValueError("new agent runs must start in running state")
        with get_session_factory().begin() as session:
            session.add(AgentRunRecord(**asdict(run)))
        return run

    def finish(self, run_id: UUID, status: str, *, result=None, usage=None, error_code=None) -> AgentRun:
        if status not in {"succeeded", "failed"} or (status == "succeeded" and result is None):
            raise ValueError("invalid agent terminal state")
        with get_session_factory().begin() as session:
            record = session.scalar(select(AgentRunRecord).where(AgentRunRecord.id == run_id).with_for_update())
            if record is None or record.status != "running":
                raise ValueError("agent run missing or already finished")
            record.status, record.result, record.usage, record.error_code = status, result, usage, error_code
            record.finished_at = datetime.now(timezone.utc)
            session.flush()
            return self._entity(record)

    def get(self, project_id: UUID, run_id: UUID) -> AgentRun | None:
        with get_session_factory()() as session:
            record = session.scalar(select(AgentRunRecord).where(
                AgentRunRecord.id == run_id, AgentRunRecord.project_id == project_id))
            return self._entity(record) if record else None

    @staticmethod
    def _entity(record: AgentRunRecord) -> AgentRun:
        return AgentRun(**{name: getattr(record, name) for name in AgentRun.__dataclass_fields__})
