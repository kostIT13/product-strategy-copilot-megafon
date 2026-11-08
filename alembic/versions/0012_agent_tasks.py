"""Task-specific typed agent outputs, preserving existing answer checkpoints."""
from alembic import op
import sqlalchemy as sa

revision = "0012_agent_tasks"
down_revision = "0011_agent_pipelines"
branch_labels = None
depends_on = None


def upgrade():
    for table in ("agent_runs", "agent_pipelines"):
        op.add_column(table, sa.Column("task", sa.String(40), nullable=False, server_default="evidence_answer"))
        op.create_check_constraint(op.f(f"ck_{table}_task_allowed"), table,
                                   "task IN ('evidence_answer', 'evidence_extraction')")


def downgrade():
    # Refuse to discard the identity of extraction outputs as if they were answers.
    connection = op.get_bind()
    for table in ("agent_runs", "agent_pipelines"):
        if connection.scalar(sa.text(f"SELECT count(*) FROM {table} WHERE task <> 'evidence_answer'")):
            raise RuntimeError("cannot downgrade while task-specific agent records exist")
    for table in ("agent_pipelines", "agent_runs"):
        op.drop_constraint(op.f(f"ck_{table}_task_allowed"), table, type_="check")
        op.drop_column(table, "task")
