"""M4 shot / render_plan / generation_attempt tables

Revision ID: 20261010_0004
Revises: 20261010_0003
Create Date: 2026-10-10
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261010_0004"
down_revision: Union[str, None] = "20261010_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "shots",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("beat_id", sa.String(32), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("render_spec_json", sa.JSON(), nullable=False),
        sa.Column("stale_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_shots_beat_id", "shots", ["beat_id"])

    op.create_table(
        "render_plans",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("shot_id", sa.String(32), nullable=False),
        sa.Column("shot_revision", sa.Integer(), nullable=False),
        sa.Column("capability", sa.String(64), nullable=False),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("template_id", sa.String(128), nullable=False),
        sa.Column("refs_json", sa.JSON(), nullable=False),
        sa.Column("stale_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_render_plans_shot_id", "render_plans", ["shot_id"])

    op.create_table(
        "generation_attempts",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("render_plan_id", sa.String(32), nullable=False),
        sa.Column("based_on_shot_revision", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("seed", sa.Integer(), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("workflow_hash", sa.String(128), nullable=False),
        sa.Column("output_asset_ids_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_generation_attempts_render_plan_id", "generation_attempts", ["render_plan_id"])


def downgrade() -> None:
    op.drop_table("generation_attempts")
    op.drop_table("render_plans")
    op.drop_table("shots")
