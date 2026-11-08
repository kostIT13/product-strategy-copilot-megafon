"""Project-bound immutable audit of canonicalizing reviewed strategy drafts."""
from uuid import UUID
from sqlalchemy import CheckConstraint, ForeignKey, ForeignKeyConstraint, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid
from product_strategy_agent.adapters.persistence.postgres.base import Base


class StrategySelectionRecord(Base):
    __tablename__ = "strategy_selections"
    __table_args__ = (
        UniqueConstraint("project_id", "source_run_id", name="uq_strategy_selections_project_run"),
        *[ForeignKeyConstraint([column, "project_id"], [f"{table}.id", f"{table}.project_id"],
                              name=f"fk_selection_{column}_project") for column, table in
          (("source_run_id", "agent_runs"), ("critic_run_id", "agent_runs"), ("decision_id", "decisions"),
           ("o1_id", "options"), ("o2_id", "options"), ("o3_id", "options"))],
        CheckConstraint("o1_id <> o2_id AND o1_id <> o3_id AND o2_id <> o3_id", name="distinct_options"),
    )
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    project_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    source_run_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    critic_run_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    decision_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    o1_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    o2_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    o3_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
