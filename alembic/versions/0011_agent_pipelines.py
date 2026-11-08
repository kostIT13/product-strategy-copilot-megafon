"""Checkpointed pipelines with atomically reserved model attempts."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0011_agent_pipelines"
down_revision = "0010_agent_runs"
branch_labels = None
depends_on = None


def upgrade():
    op.create_unique_constraint("uq_agent_runs_id_project", "agent_runs", ["id", "project_id"])
    op.create_table("agent_pipelines",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False), sa.Column("query", sa.Text(), nullable=False),
        sa.Column("model", sa.String(250), nullable=False), sa.Column("prompt_version", sa.String(100), nullable=False),
        sa.Column("provider_config_hash", sa.String(64), nullable=False), sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("contexts", postgresql.JSONB(), nullable=False),
        sa.Column("agent_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("result", postgresql.JSONB(), nullable=True), sa.Column("error_code", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('prepared', 'draft_running', 'draft_ready', 'completed', 'failed')", name=op.f("ck_agent_pipelines_status_allowed")),
        sa.CheckConstraint("version >= 0", name=op.f("ck_agent_pipelines_version_nonnegative")),
        sa.CheckConstraint("(status = 'prepared' AND agent_run_id IS NULL) OR (status <> 'prepared' AND agent_run_id IS NOT NULL)", name=op.f("ck_agent_pipelines_run_required")),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], name="fk_agent_pipelines_project_id_projects", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["agent_run_id", "project_id"], ["agent_runs.id", "agent_runs.project_id"], name="fk_agent_pipeline_run_project"),
        sa.PrimaryKeyConstraint("id", name="pk_agent_pipelines"))
    op.create_index("ix_agent_pipelines_project_created", "agent_pipelines", ["project_id", "created_at"])


def downgrade():
    op.drop_index("ix_agent_pipelines_project_created", table_name="agent_pipelines")
    op.drop_table("agent_pipelines")
    op.drop_constraint("uq_agent_runs_id_project", "agent_runs", type_="unique")
