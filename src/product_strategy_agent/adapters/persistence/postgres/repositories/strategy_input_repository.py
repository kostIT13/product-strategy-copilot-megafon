"""Content-addressed immutable context, scoped by project and pinned hash."""
from uuid import UUID
from sqlalchemy.dialects.postgresql import insert
from product_strategy_agent.adapters.persistence.postgres.database import get_session_factory
from product_strategy_agent.adapters.persistence.postgres.models import StrategyInputRecord
from product_strategy_agent.application.services.agent_context import review_target_hash


class PostgresStrategyInputStore:
    def get(self, project_id, input_hash):
        with get_session_factory()() as session:
            row = session.get(StrategyInputRecord, (project_id, input_hash))
            return row.snapshot if row else None

    def put(self, project_id, input_hash, snapshot):
        if review_target_hash(snapshot) != input_hash:
            raise ValueError("strategy input snapshot hash mismatch")
        with get_session_factory().begin() as session:
            session.execute(insert(StrategyInputRecord).values(project_id=project_id, input_hash=input_hash,
                source_run_id=UUID(snapshot["source_run_id"]), decision_id=UUID(snapshot["decision"]["id"]), snapshot=snapshot)
                .on_conflict_do_nothing(index_elements=[StrategyInputRecord.project_id, StrategyInputRecord.input_hash]))
            row = session.get(StrategyInputRecord, (project_id, input_hash))
            if row.snapshot != snapshot or str(row.source_run_id) != snapshot["source_run_id"] or str(row.decision_id) != snapshot["decision"]["id"]:
                raise ValueError("strategy input is immutable")
