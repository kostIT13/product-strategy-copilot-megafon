"""PostgreSQL mappings for claims and their citations."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from product_strategy_agent.adapters.persistence.postgres.base import Base


class ClaimRecord(Base):
    __tablename__ = "claims"
    __table_args__ = (
        UniqueConstraint("project_id", "key", name="uq_claims_project_key"),
        CheckConstraint(
            "claim_type IN ('fact', 'interpretation', 'hypothesis', 'forecast', 'synthetic')",
            name="claim_type_allowed",
        ),
        CheckConstraint("confidence IN ('low', 'medium', 'high')", name="confidence_allowed"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    key: Mapped[str] = mapped_column(String(64), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    claim_type: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence: Mapped[str] = mapped_column(String(16), nullable=False)
    reasoning_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    decision_impact: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", server_default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ClaimEvidenceRecord(Base):
    __tablename__ = "claim_evidence"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    claim_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("claims.id", ondelete="CASCADE"), nullable=False
    )
    source_revision_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("source_revisions.id", ondelete="RESTRICT"), nullable=False
    )
    locator: Mapped[str] = mapped_column(String(500), nullable=False)
    quote: Mapped[str] = mapped_column(Text, nullable=False)
