"""Create sources and immutable source revision tables."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0002_create_sources"
down_revision: str | None = "0001_create_projects"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("uri", sa.Text(), nullable=False),
        sa.Column("uri_hash", sa.String(length=64), nullable=False),
        sa.Column("kind", sa.String(length=40), nullable=False),
        sa.Column("publisher", sa.Text(), nullable=True),
        sa.Column("reliability", sa.String(length=32), server_default="unassessed", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="extracted", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], name="fk_sources_project_id_projects", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_sources"),
        sa.UniqueConstraint("project_id", "uri_hash", name="uq_sources_project_uri_hash"),
    )
    op.create_table(
        "source_revisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=False),
        sa.Column("locator", sa.String(length=500), nullable=False),
        sa.Column("accessed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("limitations", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], name="fk_source_revisions_source_id_sources", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_source_revisions"),
        sa.UniqueConstraint("source_id", "content_hash", name="uq_source_revisions_source_hash"),
        sa.UniqueConstraint("source_id", "revision", name="uq_source_revisions_source_revision"),
    )


def downgrade() -> None:
    op.drop_table("source_revisions")
    op.drop_table("sources")
