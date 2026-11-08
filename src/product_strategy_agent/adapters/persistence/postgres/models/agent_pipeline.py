"""Versioned orchestration state with a project-bound paid attempt reference."""
from datetime import datetime
from uuid import UUID
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid
from product_strategy_agent.adapters.persistence.postgres.base import Base


class AgentPipelineRecord(Base):
    __tablename__ = "agent_pipelines"
    __table_args__ = (
        CheckConstraint("task IN ('evidence_answer', 'evidence_extraction')", name="task_allowed"),
        CheckConstraint("status IN ('prepared', 'draft_running', 'draft_ready', 'completed', 'failed')", name="status_allowed"),
        CheckConstraint("version >= 0", name="version_nonnegative"),
        CheckConstraint("(status = 'prepared' AND agent_run_id IS NULL) OR (status <> 'prepared' AND agent_run_id IS NOT NULL)", name="run_required"),
        ForeignKeyConstraint(["agent_run_id", "project_id"], ["agent_runs.id", "agent_runs.project_id"], name="fk_agent_pipeline_run_project"),
        Index("ix_agent_pipelines_project_created", "project_id", "created_at"),
    )
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    project_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(String(250), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(100), nullable=False)
    provider_config_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    contexts: Mapped[list[dict]] = mapped_column(JSONB, nullable=False)
    agent_run_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    task: Mapped[str] = mapped_column(String(40), nullable=False, server_default="evidence_answer")
