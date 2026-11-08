"""Project-bound critic targets with content hashes, preserving old requests."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0013_critic_inputs"
down_revision = "0012_agent_tasks"
branch_labels = None
depends_on = None


def upgrade():
    for table in ("agent_runs", "agent_pipelines"):
        op.add_column(table, sa.Column("input_run_id", postgresql.UUID(as_uuid=True), nullable=True))
        op.add_column(table, sa.Column("input_hash", sa.String(64), nullable=True))
        op.drop_constraint(op.f(f"ck_{table}_task_allowed"), table, type_="check")
        op.create_check_constraint(op.f(f"ck_{table}_task_allowed"), table,
                                   "task IN ('evidence_answer', 'evidence_extraction', 'evidence_critic')")
        op.create_check_constraint(op.f(f"ck_{table}_input_required"), table,
            "(task = 'evidence_critic' AND input_run_id IS NOT NULL AND input_hash IS NOT NULL) OR "
            "(task <> 'evidence_critic' AND input_run_id IS NULL AND input_hash IS NULL)")
        op.create_foreign_key(f"fk_{table}_input_project", table, "agent_runs",
                              ["input_run_id", "project_id"], ["id", "project_id"])


def downgrade():
    connection = op.get_bind()
    for table in ("agent_runs", "agent_pipelines"):
        if connection.scalar(sa.text(f"SELECT count(*) FROM {table} WHERE task = 'evidence_critic'")):
            raise RuntimeError("cannot downgrade while linked critic records exist")
    for table in ("agent_pipelines", "agent_runs"):
        op.drop_constraint(f"fk_{table}_input_project", table, type_="foreignkey")
        op.drop_constraint(op.f(f"ck_{table}_input_required"), table, type_="check")
        op.drop_constraint(op.f(f"ck_{table}_task_allowed"), table, type_="check")
        op.create_check_constraint(op.f(f"ck_{table}_task_allowed"), table,
                                   "task IN ('evidence_answer', 'evidence_extraction')")
        op.drop_column(table, "input_hash")
        op.drop_column(table, "input_run_id")
