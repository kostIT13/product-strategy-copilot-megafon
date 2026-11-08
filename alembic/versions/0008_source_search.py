"""Index source revision titles and text for project-scoped retrieval."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0008_source_search"
down_revision = "0007_create_workflow"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("source_revisions", sa.Column("search_vector", postgresql.TSVECTOR(), sa.Computed(
        "setweight(to_tsvector('pg_catalog.simple'::regconfig, coalesce(title, '')), 'A') || "
        "setweight(to_tsvector('pg_catalog.simple'::regconfig, left(coalesce(extracted_text, ''), 100000)), 'B')",
        persisted=True,
    ), nullable=False))
    op.create_index("ix_source_revisions_search_vector", "source_revisions", ["search_vector"], postgresql_using="gin")


def downgrade():
    op.drop_index("ix_source_revisions_search_vector", table_name="source_revisions")
    op.drop_column("source_revisions", "search_vector")
