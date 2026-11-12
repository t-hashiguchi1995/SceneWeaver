"""Frozen job execution snapshot persistence."""

import sqlalchemy as sa
from alembic import op

revision = "20261113_0010"
down_revision = "20261111_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("snapshot_json", sa.Text, nullable=True))
    op.add_column("jobs", sa.Column("snapshot_hash", sa.String(64), nullable=True))
    op.add_column("jobs", sa.Column("snapshot_schema_version", sa.Integer, nullable=True))


def downgrade() -> None:
    op.drop_column("jobs", "snapshot_schema_version")
    op.drop_column("jobs", "snapshot_hash")
    op.drop_column("jobs", "snapshot_json")
