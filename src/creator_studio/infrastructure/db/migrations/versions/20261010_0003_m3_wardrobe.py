"""M3 wardrobe / try-on tables + marketplace FTS5

Revision ID: 20261010_0003
Revises: 20261010_0002
Create Date: 2026-10-10
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261010_0003"
down_revision: Union[str, None] = "20261010_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "marketplace_items",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("region", sa.String(64), nullable=False),
        sa.Column("style_tags_json", sa.JSON(), nullable=False),
        sa.Column("season_tags_json", sa.JSON(), nullable=False),
        sa.Column("colors_json", sa.JSON(), nullable=False),
        sa.Column("garment_description", sa.Text(), nullable=False),
        sa.Column("canonical_plate_asset_id", sa.String(32), nullable=True),
        sa.Column("source_json", sa.JSON(), nullable=False),
        sa.Column("verification_json", sa.JSON(), nullable=False),
        sa.Column("search_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_marketplace_items_category", "marketplace_items", ["category"])
    op.create_index("ix_marketplace_items_region", "marketplace_items", ["region"])

    op.create_table(
        "outfit_profiles",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("character_id", sa.String(32), nullable=True),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("marketplace_item_id", sa.String(32), nullable=True),
        sa.Column("semantic_json", sa.JSON(), nullable=False),
        sa.Column("references_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_outfit_profiles_character_id", "outfit_profiles", ["character_id"])

    op.create_table(
        "tryon_sessions",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("character_id", sa.String(32), nullable=False),
        sa.Column("outfit_profile_id", sa.String(32), nullable=False),
        sa.Column("source_asset_id", sa.String(32), nullable=False),
        sa.Column("plate_asset_id", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("candidate_asset_ids_json", sa.JSON(), nullable=False),
        sa.Column("adopted_asset_id", sa.String(32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_tryon_sessions_character_id", "tryon_sessions", ["character_id"])

    # FTS5 is SQLite-native; not represented in SQLAlchemy metadata.
    op.execute(
        """
        CREATE VIRTUAL TABLE marketplace_items_fts USING fts5(
            item_id UNINDEXED,
            title,
            garment_description,
            style_tags
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS marketplace_items_fts")
    op.drop_table("tryon_sessions")
    op.drop_table("outfit_profiles")
    op.drop_table("marketplace_items")
