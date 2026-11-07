"""Persist agent execution metadata and validated answer drafts."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0010_agent_runs"
down_revision = "0009_source_provenance"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("agent_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("model", sa.String(250), nullable=False),
        sa.Column("prompt_version", sa.String(100), nullable=False),
        sa.Column("contexts", postgresql.JSONB(), nullable=False),
        sa.Column("result", postgresql.JSONB(), nullable=True),
        sa.Column("usage", postgresql.JSONB(), nullable=True),
        sa.Column("error_code", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('running', 'succeeded', 'failed')", name=op.f("ck_agent_runs_status_allowed")),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], name="fk_agent_runs_project_id_projects", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_agent_runs"))
    op.create_index("ix_agent_runs_project_created", "agent_runs", ["project_id", "created_at"])


def downgrade():
    op.drop_index("ix_agent_runs_project_created", table_name="agent_runs")
    op.drop_table("agent_runs")
