from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from creator_studio.infrastructure.db.base import Base


class ShotRow(Base):
    __tablename__ = "shots"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    beat_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    render_spec_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    stale_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_prompt_draft_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RenderPlanRow(Base):
    __tablename__ = "render_plans"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    shot_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    shot_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    capability: Mapped[str] = mapped_column(String(64), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    template_id: Mapped[str] = mapped_column(String(128), nullable=False)
    refs_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    stale_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class GenerationAttemptRow(Base):
    """Immutable row — Application never UPDATEs provenance fields after insert."""

    __tablename__ = "generation_attempts"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    render_plan_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    based_on_shot_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    seed: Mapped[int] = mapped_column(Integer, nullable=False)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    workflow_hash: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    output_asset_ids_json: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
