"""Human internal approval audit for decision-bound strategies."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0017_strategy_approvals"
down_revision = "0016_strategy_plans"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("strategy_approvals",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        *[sa.Column(name, sa.Uuid(), nullable=False) for name in ("strategy_run_id", "critic_run_id", "decision_id")],
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.UniqueConstraint("project_id", "strategy_run_id", name="uq_strategy_approvals_project_run"),
        *[sa.ForeignKeyConstraint([column, "project_id"], [f"{table}.id", f"{table}.project_id"],
                                 name=f"fk_strategy_approval_{column}_project") for column, table in
          (("strategy_run_id", "agent_runs"), ("critic_run_id", "agent_runs"), ("decision_id", "decisions"))])


def downgrade():
    if op.get_bind().scalar(sa.text("SELECT count(*) FROM strategy_approvals")):
        raise RuntimeError("cannot downgrade while human strategy approvals exist")
    op.drop_table("strategy_approvals")
