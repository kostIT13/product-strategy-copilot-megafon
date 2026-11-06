"""PostgreSQL mappings for workflow state and append-only events."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from product_strategy_agent.adapters.persistence.postgres.base import Base

_STAGE_CHECK = "stage IN ('intake', 'research_plan', 'source_collection', 'evidence_review', 'options', 'strategy', 'validation', 'completed')"


class WorkflowStateRecord(Base):
    __tablename__ = "workflow_states"
    __table_args__ = (
        CheckConstraint(_STAGE_CHECK, name="current_stage_allowed"),
        CheckConstraint("status IN ('in_progress', 'completed')", name="status_allowed"),
    )

    project_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True
    )
    current_stage: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="in_progress", server_default="in_progress")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class WorkflowEventRecord(Base):
    __tablename__ = "workflow_events"
    __table_args__ = (
        UniqueConstraint("project_id", "sequence", name="uq_workflow_events_project_sequence"),
        CheckConstraint(_STAGE_CHECK.replace("stage", "to_stage"), name="to_stage_allowed"),
        CheckConstraint("sequence > 0", name="sequence_positive"),
        CheckConstraint(
            "from_stage IS NULL OR " + _STAGE_CHECK.replace("stage", "from_stage"),
            name="from_stage_allowed",
        ),
        CheckConstraint("event_type IN ('started', 'stage_approved')", name="event_type_allowed"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    from_stage: Mapped[str | None] = mapped_column(String(32), nullable=True)
    to_stage: Mapped[str] = mapped_column(String(32), nullable=False)
    actor: Mapped[str] = mapped_column(String(200), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
