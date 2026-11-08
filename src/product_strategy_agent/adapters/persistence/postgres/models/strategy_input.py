"""Immutable, project-bound context cached before a strategy pipeline starts."""
from uuid import UUID
from sqlalchemy import ForeignKey, ForeignKeyConstraint, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid
from product_strategy_agent.adapters.persistence.postgres.base import Base


class StrategyInputRecord(Base):
    __tablename__ = "strategy_inputs"
    __table_args__ = (
        ForeignKeyConstraint(["source_run_id", "project_id"], ["agent_runs.id", "agent_runs.project_id"], name="fk_strategy_input_run_project"),
        ForeignKeyConstraint(["decision_id", "project_id"], ["decisions.id", "decisions.project_id"], name="fk_strategy_input_decision_project"),
    )
    project_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True)
    input_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_run_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    decision_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
