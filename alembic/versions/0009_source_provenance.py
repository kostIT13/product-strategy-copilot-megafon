"""Store structured extraction/fetch provenance with source revisions."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0009_source_provenance"
down_revision = "0008_source_search"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("source_revisions", sa.Column("provenance", postgresql.JSONB(),
        nullable=False, server_default=sa.text("'{}'::jsonb")))


def downgrade():
    op.drop_column("source_revisions", "provenance")
