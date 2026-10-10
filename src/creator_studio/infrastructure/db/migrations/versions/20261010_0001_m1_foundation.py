"""M1 foundation tables

Revision ID: 20261010_0001
Revises:
Create Date: 2026-10-10
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261010_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("content_rating", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "jobs",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("progress_json", sa.JSON(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("lease_owner", sa.String(length=128), nullable=True),
        sa.Column("leased_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("external_job_ref", sa.String(length=256), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_jobs_kind", "jobs", ["kind"])
    op.create_index("ix_jobs_status", "jobs", ["status"])
    op.create_index("ix_jobs_idempotency_key", "jobs", ["idempotency_key"], unique=True)

    op.create_table(
        "assets",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("uri", sa.String(length=1024), nullable=False),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("mime", sa.String(length=128), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("provenance_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_assets_sha256", "assets", ["sha256"])

    op.create_table(
        "asset_links",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("asset_id", sa.String(length=32), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.String(length=32), nullable=False),
        sa.Column("role", sa.String(length=64), nullable=False),
        sa.UniqueConstraint("asset_id", "entity_type", "entity_id", "role", name="uq_asset_link"),
    )
    op.create_index("ix_asset_links_asset_id", "asset_links", ["asset_id"])


def downgrade() -> None:
    op.drop_table("asset_links")
    op.drop_table("assets")
    op.drop_index("ix_jobs_idempotency_key", table_name="jobs")
    op.drop_index("ix_jobs_status", table_name="jobs")
    op.drop_index("ix_jobs_kind", table_name="jobs")
    op.drop_table("jobs")
    op.drop_table("projects")