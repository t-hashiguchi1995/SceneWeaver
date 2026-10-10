"""M2 story / character tables

Revision ID: 20261010_0002
Revises: 20261010_0001
Create Date: 2026-10-10
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261010_0002"
down_revision: Union[str, None] = "20261010_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "characters",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("display_name", sa.String(256), nullable=False),
        sa.Column("visual_identity_json", sa.JSON(), nullable=False),
        sa.Column("persona_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "scenes",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("project_id", sa.String(32), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("initial_state_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_scenes_project_id", "scenes", ["project_id"])
    op.create_table(
        "beats",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("scene_id", sa.String(32), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("intent", sa.Text(), nullable=False),
        sa.Column("subtext", sa.Text(), nullable=False),
        sa.Column("emotion_json", sa.JSON(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("speaker_id", sa.String(32), nullable=True),
        sa.Column("state_delta_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_beats_scene_id", "beats", ["scene_id"])
    op.create_table(
        "script_events",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("beat_id", sa.String(32), nullable=False),
        sa.Column("kind", sa.String(64), nullable=False),
        sa.Column("speaker_id", sa.String(32), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("locked", sa.Boolean(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("tone", sa.String(128), nullable=False),
        sa.Column("critic_scores_json", sa.JSON(), nullable=False),
        sa.Column("director_plan_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_script_events_beat_id", "script_events", ["beat_id"])


def downgrade() -> None:
    op.drop_table("script_events")
    op.drop_table("beats")
    op.drop_table("scenes")
    op.drop_table("characters")