"""Audit explicit human choices and atomically adopted strategy alternatives."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0015_strategy_selections"
down_revision = "0014_strategy_options"
branch_labels = None
depends_on = None


def upgrade():
    for table in ("options", "decisions"):
        op.create_unique_constraint(f"uq_{table}_id_project", table, ["id", "project_id"])
    op.create_table("strategy_selections",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        *[sa.Column(name, sa.Uuid(), nullable=False) for name in
          ("source_run_id", "critic_run_id", "decision_id", "o1_id", "o2_id", "o3_id")],
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.UniqueConstraint("project_id", "source_run_id", name="uq_strategy_selections_project_run"),
        *[sa.ForeignKeyConstraint([column, "project_id"], [f"{table}.id", f"{table}.project_id"],
                                 name=f"fk_selection_{column}_project") for column, table in
          (("source_run_id", "agent_runs"), ("critic_run_id", "agent_runs"), ("decision_id", "decisions"),
           ("o1_id", "options"), ("o2_id", "options"), ("o3_id", "options"))],
        sa.CheckConstraint("o1_id <> o2_id AND o1_id <> o3_id AND o2_id <> o3_id", name=op.f("ck_strategy_selections_distinct_options")))


def downgrade():
    if op.get_bind().scalar(sa.text("SELECT count(*) FROM strategy_selections")):
        raise RuntimeError("cannot downgrade while human strategy selections exist")
    op.drop_table("strategy_selections")
    for table in ("decisions", "options"):
        op.drop_constraint(f"uq_{table}_id_project", table, type_="unique")
