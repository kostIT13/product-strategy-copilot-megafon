"""Create current workflow state and append-only transition history."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0007_create_workflow"
down_revision: str | None = "0006_create_capabilities"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_STAGES = "'intake', 'research_plan', 'source_collection', 'evidence_review', 'options', 'strategy', 'validation', 'completed'"


def upgrade() -> None:
    op.create_table(
        "workflow_states",
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("current_stage", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="in_progress", nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(f"current_stage IN ({_STAGES})", name="ck_workflow_states_current_stage_allowed"),
        sa.CheckConstraint("status IN ('in_progress', 'completed')", name="ck_workflow_states_status_allowed"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], name="fk_workflow_states_project_id_projects", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("project_id", name="pk_workflow_states"),
    )
    op.create_table(
        "workflow_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("from_stage", sa.String(length=32), nullable=True),
        sa.Column("to_stage", sa.String(length=32), nullable=False),
        sa.Column("actor", sa.String(length=200), nullable=False),
        sa.Column("reason", sa.Text(), server_default="", nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(f"to_stage IN ({_STAGES})", name="ck_workflow_events_to_stage_allowed"),
        sa.CheckConstraint(f"from_stage IS NULL OR from_stage IN ({_STAGES})", name="ck_workflow_events_from_stage_allowed"),
        sa.CheckConstraint("event_type IN ('started', 'stage_approved')", name="ck_workflow_events_event_type_allowed"),
        sa.CheckConstraint("sequence > 0", name="ck_workflow_events_sequence_positive"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], name="fk_workflow_events_project_id_projects", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_workflow_events"),
        sa.UniqueConstraint("project_id", "sequence", name="uq_workflow_events_project_sequence"),
    )


def downgrade() -> None:
    op.drop_table("workflow_events")
    op.drop_table("workflow_states")
