"""PostgreSQL mappings for decisions and their traceable references."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from product_strategy_agent.adapters.persistence.postgres.base import Base


class DecisionRecord(Base):
    __tablename__ = "decisions"
    __table_args__ = (UniqueConstraint("project_id", "key", name="uq_decisions_project_key"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    key: Mapped[str] = mapped_column(String(64), nullable=False)
    selected_option_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("options.id", ondelete="RESTRICT"), nullable=False
    )
    owner: Mapped[str] = mapped_column(String(200), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    assumptions: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))
    risks: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))
    review_trigger: Mapped[str] = mapped_column(Text, nullable=False)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DecisionOptionRecord(Base):
    __tablename__ = "decision_options"
    __table_args__ = (
        UniqueConstraint("decision_id", "option_id", name="uq_decision_options_decision_option"),
        CheckConstraint("disposition IN ('selected', 'rejected', 'deferred')", name="disposition_allowed"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    decision_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("decisions.id", ondelete="CASCADE"), nullable=False
    )
    option_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("options.id", ondelete="RESTRICT"), nullable=False
    )
    disposition: Mapped[str] = mapped_column(String(16), nullable=False)


class DecisionClaimRecord(Base):
    __tablename__ = "decision_claims"
    __table_args__ = (
        UniqueConstraint("decision_id", "claim_id", name="uq_decision_claims_decision_claim"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    decision_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("decisions.id", ondelete="CASCADE"), nullable=False
    )
    claim_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("claims.id", ondelete="RESTRICT"), nullable=False
    )
