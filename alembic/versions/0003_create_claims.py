"""Create claims and source-revision evidence links."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0003_create_claims"
down_revision: str | None = "0002_create_sources"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "claims",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("claim_type", sa.String(length=32), nullable=False),
        sa.Column("confidence", sa.String(length=16), nullable=False),
        sa.Column("reasoning_note", sa.Text(), nullable=True),
        sa.Column("decision_impact", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "claim_type IN ('fact', 'interpretation', 'hypothesis', 'forecast', 'synthetic')",
            name="ck_claims_claim_type_allowed",
        ),
        sa.CheckConstraint("confidence IN ('low', 'medium', 'high')", name="ck_claims_confidence_allowed"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], name="fk_claims_project_id_projects", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_claims"),
        sa.UniqueConstraint("project_id", "key", name="uq_claims_project_key"),
    )
    op.create_table(
        "claim_evidence",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("claim_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_revision_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("locator", sa.String(length=500), nullable=False),
        sa.Column("quote", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["claim_id"], ["claims.id"], name="fk_claim_evidence_claim_id_claims", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_revision_id"], ["source_revisions.id"], name="fk_claim_evidence_source_revision_id_source_revisions", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_claim_evidence"),
    )


def downgrade() -> None:
    op.drop_table("claim_evidence")
    op.drop_table("claims")
