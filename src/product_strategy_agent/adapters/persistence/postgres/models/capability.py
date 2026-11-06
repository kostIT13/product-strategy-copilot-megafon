"""PostgreSQL mappings for product capabilities."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from product_strategy_agent.adapters.persistence.postgres.base import Base


class CapabilityRecord(Base):
    __tablename__ = "capabilities"
    __table_args__ = (
        UniqueConstraint("project_id", "key", name="uq_capabilities_project_key"),
        CheckConstraint(
            "status IN ('available', 'planned', 'unavailable')",
            name="status_allowed",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    key: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(250), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class CapabilityClaimRecord(Base):
    __tablename__ = "capability_claims"
    __table_args__ = (UniqueConstraint("capability_id", "claim_id", name="uq_capability_claims_capability_claim"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    capability_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("capabilities.id", ondelete="CASCADE"), nullable=False
    )
    claim_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("claims.id", ondelete="RESTRICT"), nullable=False
    )
