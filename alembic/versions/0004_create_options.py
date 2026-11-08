"""Create strategy options and evidence links."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0004_create_options"
down_revision: str | None = "0003_create_claims"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "options",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=250), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("strengths", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("risks", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("assumptions", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="proposed", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], name="fk_options_project_id_projects", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_options"),
        sa.UniqueConstraint("project_id", "key", name="uq_options_project_key"),
    )
    op.create_table(
        "option_claims",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("option_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("claim_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("relation", sa.String(length=16), nullable=False),
        sa.CheckConstraint("relation IN ('supports', 'challenges')", name="ck_option_claims_relation_allowed"),
        sa.ForeignKeyConstraint(["claim_id"], ["claims.id"], name="fk_option_claims_claim_id_claims", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["option_id"], ["options.id"], name="fk_option_claims_option_id_options", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_option_claims"),
        sa.UniqueConstraint("option_id", "claim_id", name="uq_option_claims_option_claim"),
    )


def downgrade() -> None:
    op.drop_table("option_claims")
    op.drop_table("options")
