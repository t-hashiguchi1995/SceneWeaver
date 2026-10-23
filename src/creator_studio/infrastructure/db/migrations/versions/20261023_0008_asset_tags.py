"""Asset auto-tags from ImageTagger (PixAI / stub)."""
from alembic import op
import sqlalchemy as sa

revision = "20261023_0008"
down_revision = "20261018_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "asset_tags",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("asset_id", sa.String(length=32), nullable=False),
        sa.Column("tag", sa.String(length=256), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("source_model", sa.String(length=128), nullable=False),
        sa.Column("model_version", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "asset_id",
            "tag",
            "source_model",
            "model_version",
            name="uq_asset_tag_identity",
        ),
    )
    op.create_index("ix_asset_tags_asset_id", "asset_tags", ["asset_id"])
    op.create_index("ix_asset_tags_tag", "asset_tags", ["tag"])


def downgrade() -> None:
    op.drop_index("ix_asset_tags_tag", table_name="asset_tags")
    op.drop_index("ix_asset_tags_asset_id", table_name="asset_tags")
    op.drop_table("asset_tags")
