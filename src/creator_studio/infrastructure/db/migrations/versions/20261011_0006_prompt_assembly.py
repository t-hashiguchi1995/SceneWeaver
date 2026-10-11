"""Persist assembly provenance on mutable drafts for immutable attempt snapshots."""
from alembic import op
import sqlalchemy as sa

revision = "20261011_0006"
down_revision = "20261010_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("prompt_drafts", sa.Column("assembly_metadata_json", sa.JSON(), nullable=False, server_default="{}"))


def downgrade() -> None:
    op.drop_column("prompt_drafts", "assembly_metadata_json")
