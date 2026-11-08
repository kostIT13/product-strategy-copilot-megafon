"""Allow evidence-grounded strategy proposal runs and checkpoints."""
from alembic import op
import sqlalchemy as sa

revision = "0014_strategy_options"
down_revision = "0013_critic_inputs"
branch_labels = None
depends_on = None


def upgrade():
    for table in ("agent_runs", "agent_pipelines"):
        op.drop_constraint(op.f(f"ck_{table}_task_allowed"), table, type_="check")
        op.create_check_constraint(op.f(f"ck_{table}_task_allowed"), table,
            "task IN ('evidence_answer', 'evidence_extraction', 'strategy_options', 'evidence_critic')")


def downgrade():
    connection = op.get_bind()
    for table in ("agent_runs", "agent_pipelines"):
        if connection.scalar(sa.text(f"SELECT count(*) FROM {table} WHERE task = 'strategy_options'")):
            raise RuntimeError("cannot downgrade while strategy proposal records exist")
    for table in ("agent_pipelines", "agent_runs"):
        op.drop_constraint(op.f(f"ck_{table}_task_allowed"), table, type_="check")
        op.create_check_constraint(op.f(f"ck_{table}_task_allowed"), table,
            "task IN ('evidence_answer', 'evidence_extraction', 'evidence_critic')")
