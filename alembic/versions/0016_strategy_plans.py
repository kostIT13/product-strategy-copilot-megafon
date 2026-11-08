"""Decision-bound planning task and immutable input contexts."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0016_strategy_plans"
down_revision = "0015_strategy_selections"
branch_labels = None
depends_on = None


def guards(include_plan):
    tasks = "'evidence_answer', 'evidence_extraction', 'strategy_options', 'evidence_critic'" + (", 'strategy_plan'" if include_plan else "")
    bound = "'evidence_critic', 'strategy_plan'" if include_plan else "'evidence_critic'"
    for table in ("agent_runs", "agent_pipelines"):
        for name in ("task_allowed", "input_required"):
            op.drop_constraint(op.f(f"ck_{table}_{name}"), table, type_="check")
        op.create_check_constraint(op.f(f"ck_{table}_task_allowed"), table, f"task IN ({tasks})")
        op.create_check_constraint(op.f(f"ck_{table}_input_required"), table,
            f"(task IN ({bound}) AND input_run_id IS NOT NULL AND input_hash IS NOT NULL) OR "
            f"(task NOT IN ({bound}) AND input_run_id IS NULL AND input_hash IS NULL)")


def upgrade():
    guards(True)
    op.create_table("strategy_inputs",
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("input_hash", sa.String(64), primary_key=True),
        sa.Column("source_run_id", sa.Uuid(), nullable=False),
        sa.Column("decision_id", sa.Uuid(), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(), nullable=False),
        sa.ForeignKeyConstraint(["source_run_id", "project_id"], ["agent_runs.id", "agent_runs.project_id"], name="fk_strategy_input_run_project"),
        sa.ForeignKeyConstraint(["decision_id", "project_id"], ["decisions.id", "decisions.project_id"], name="fk_strategy_input_decision_project"))


def downgrade():
    connection = op.get_bind()
    if connection.scalar(sa.text("SELECT count(*) FROM strategy_inputs")) or any(
        connection.scalar(sa.text(f"SELECT count(*) FROM {table} WHERE task = 'strategy_plan'")) for table in ("agent_runs", "agent_pipelines")):
        raise RuntimeError("cannot downgrade while strategy inputs or planning records exist")
    op.drop_table("strategy_inputs")
    guards(False)
