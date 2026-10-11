from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from creator_studio.infrastructure.db.base import Base


class PromptDraftRow(Base):
    __tablename__ = "prompt_drafts"
    __table_args__ = (
        UniqueConstraint(
            "shot_id",
            "template_id",
            "template_version",
            name="uq_prompt_drafts_shot_template",
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    shot_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    template_id: Mapped[str] = mapped_column(String(128), nullable=False)
    template_version: Mapped[str] = mapped_column(String(64), nullable=False)
    source_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    source_ref: Mapped[str] = mapped_column(String(256), nullable=False)
    source_shot_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    context_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    rendered_base_positive: Mapped[str] = mapped_column(Text, nullable=False)
    rendered_base_negative: Mapped[str] = mapped_column(Text, nullable=False)
    edited_positive: Mapped[str] = mapped_column(Text, nullable=False)
    edited_negative: Mapped[str] = mapped_column(Text, nullable=False)
    assembly_metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PromptPresetRow(Base):
    __tablename__ = "prompt_presets"
    __table_args__ = (
        UniqueConstraint(
            "source",
            "source_file",
            "legacy_key",
            name="uq_prompt_presets_legacy_identity",
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    kind: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(512), nullable=False)
    prompt_fragment: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(String(128), nullable=True)
    content_rating: Mapped[str] = mapped_column(String(32), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    source: Mapped[str] = mapped_column(String(128), nullable=False)
    source_file: Mapped[str] = mapped_column(String(512), nullable=False)
    legacy_key: Mapped[str] = mapped_column(String(256), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class LegacyImportRecordRow(Base):
    __tablename__ = "legacy_import_records"
    __table_args__ = (
        UniqueConstraint(
            "source",
            "source_file",
            "legacy_key",
            name="uq_legacy_import_identity",
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    source: Mapped[str] = mapped_column(String(128), nullable=False)
    source_file: Mapped[str] = mapped_column(String(512), nullable=False)
    legacy_key: Mapped[str] = mapped_column(String(256), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(32), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
