"""Prompt drafts + legacy import tracking

Revision ID: 20261010_0005
Revises: 20261010_0004
Create Date: 2026-10-10
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261010_0005"
down_revision: Union[str, None] = "20261010_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "shots",
        sa.Column("current_prompt_draft_id", sa.String(32), nullable=True),
    )

    op.create_table(
        "prompt_drafts",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("shot_id", sa.String(32), nullable=False),
        sa.Column("template_id", sa.String(128), nullable=False),
        sa.Column("template_version", sa.String(64), nullable=False),
        sa.Column("source_kind", sa.String(32), nullable=False),
        sa.Column("source_ref", sa.String(256), nullable=False),
        sa.Column("source_shot_revision", sa.Integer(), nullable=False),
        sa.Column("context_hash", sa.String(64), nullable=False),
        sa.Column("rendered_base_positive", sa.Text(), nullable=False),
        sa.Column("rendered_base_negative", sa.Text(), nullable=False),
        sa.Column("edited_positive", sa.Text(), nullable=False),
        sa.Column("edited_negative", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "shot_id",
            "template_id",
            "template_version",
            name="uq_prompt_drafts_shot_template",
        ),
    )
    op.create_index("ix_prompt_drafts_shot_id", "prompt_drafts", ["shot_id"])

    op.create_table(
        "prompt_presets",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("kind", sa.String(64), nullable=False),
        sa.Column("label", sa.String(512), nullable=False),
        sa.Column("prompt_fragment", sa.Text(), nullable=False),
        sa.Column("category", sa.String(128), nullable=True),
        sa.Column("content_rating", sa.String(32), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("source", sa.String(128), nullable=False),
        sa.Column("source_file", sa.String(512), nullable=False),
        sa.Column("legacy_key", sa.String(256), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "source",
            "source_file",
            "legacy_key",
            name="uq_prompt_presets_legacy_identity",
        ),
    )
    op.create_index("ix_prompt_presets_kind", "prompt_presets", ["kind"])

    op.create_table(
        "legacy_import_records",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("source", sa.String(128), nullable=False),
        sa.Column("source_file", sa.String(512), nullable=False),
        sa.Column("legacy_key", sa.String(256), nullable=False),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("entity_id", sa.String(32), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "source",
            "source_file",
            "legacy_key",
            name="uq_legacy_import_identity",
        ),
    )


def downgrade() -> None:
    op.drop_table("legacy_import_records")
    op.drop_table("prompt_presets")
    op.drop_table("prompt_drafts")
    op.drop_column("shots", "current_prompt_draft_id")
