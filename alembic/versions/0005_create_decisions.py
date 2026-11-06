"""Create decision records and references to alternatives and claims."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0005_create_decisions"
down_revision: str | None = "0004_create_options"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("selected_option_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner", sa.String(length=200), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("assumptions", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("risks", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("review_trigger", sa.Text(), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], name="fk_decisions_project_id_projects", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["selected_option_id"], ["options.id"], name="fk_decisions_selected_option_id_options", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_decisions"),
        sa.UniqueConstraint("project_id", "key", name="uq_decisions_project_key"),
    )
    op.create_table(
        "decision_options",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("decision_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("option_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("disposition", sa.String(length=16), nullable=False),
        sa.CheckConstraint("disposition IN ('selected', 'rejected', 'deferred')", name="ck_decision_options_disposition_allowed"),
        sa.ForeignKeyConstraint(["decision_id"], ["decisions.id"], name="fk_decision_options_decision_id_decisions", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["option_id"], ["options.id"], name="fk_decision_options_option_id_options", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_decision_options"),
        sa.UniqueConstraint("decision_id", "option_id", name="uq_decision_options_decision_option"),
    )
    op.create_table(
        "decision_claims",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("decision_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("claim_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["claim_id"], ["claims.id"], name="fk_decision_claims_claim_id_claims", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["decision_id"], ["decisions.id"], name="fk_decision_claims_decision_id_decisions", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_decision_claims"),
        sa.UniqueConstraint("decision_id", "claim_id", name="uq_decision_claims_decision_claim"),
    )


def downgrade() -> None:
    op.drop_table("decision_claims")
    op.drop_table("decision_options")
    op.drop_table("decisions")
