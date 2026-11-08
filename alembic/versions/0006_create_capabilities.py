"""Create product capabilities and supporting claim links."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0006_create_capabilities"
down_revision: str | None = "0005_create_decisions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "capabilities",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=250), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "status IN ('available', 'planned', 'unavailable')",
            name="ck_capabilities_status_allowed",
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], name="fk_capabilities_project_id_projects", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_capabilities"),
        sa.UniqueConstraint("project_id", "key", name="uq_capabilities_project_key"),
    )
    op.create_table(
        "capability_claims",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("capability_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("claim_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["capability_id"], ["capabilities.id"], name="fk_capability_claims_capability_id_capabilities", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["claim_id"], ["claims.id"], name="fk_capability_claims_claim_id_claims", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_capability_claims"),
        sa.UniqueConstraint("capability_id", "claim_id", name="uq_capability_claims_capability_claim"),
    )


def downgrade() -> None:
    op.drop_table("capability_claims")
    op.drop_table("capabilities")
