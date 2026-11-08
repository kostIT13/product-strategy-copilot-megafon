"""Immutable project-bound internal strategy approval receipt."""
from uuid import UUID
from sqlalchemy import ForeignKey, ForeignKeyConstraint, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid
from product_strategy_agent.adapters.persistence.postgres.base import Base


class StrategyApprovalRecord(Base):
    __tablename__ = "strategy_approvals"
    __table_args__ = (
        UniqueConstraint("project_id", "strategy_run_id", name="uq_strategy_approvals_project_run"),
        *[ForeignKeyConstraint([column, "project_id"], [f"{table}.id", f"{table}.project_id"],
                              name=f"fk_strategy_approval_{column}_project") for column, table in
          (("strategy_run_id", "agent_runs"), ("critic_run_id", "agent_runs"), ("decision_id", "decisions"))],
    )
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    project_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    strategy_run_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    critic_run_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    decision_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
