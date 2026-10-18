"""Visual Library display metadata (CE-2). Separate from PromptPreset content."""
from alembic import op
import sqlalchemy as sa

revision = "20261018_0007"
down_revision = "20261011_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "visual_library_metadata",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_id", sa.String(length=32), nullable=False),
        sa.Column("visual_kind", sa.String(length=32), nullable=False),
        sa.Column("label_ja", sa.String(length=512), nullable=True),
        sa.Column("description_ja", sa.Text(), nullable=True),
        sa.Column("thumbnail_asset_id", sa.String(length=32), nullable=True),
        sa.Column("preview_kind", sa.String(length=32), nullable=True),
        sa.Column("subcategory", sa.String(length=128), nullable=True),
        sa.Column("tags_json", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("model_scope_json", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("related_refs_json", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("source_type", "source_id", name="uq_visual_library_source"),
    )
    op.create_index(
        "ix_visual_library_metadata_visual_kind",
        "visual_library_metadata",
        ["visual_kind"],
    )


def downgrade() -> None:
    op.drop_index("ix_visual_library_metadata_visual_kind", table_name="visual_library_metadata")
    op.drop_table("visual_library_metadata")
