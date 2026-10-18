from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from creator_studio.infrastructure.db.base import Base


class VisualLibraryMetadataRow(Base):
    __tablename__ = "visual_library_metadata"
    __table_args__ = (
        UniqueConstraint("source_type", "source_id", name="uq_visual_library_source"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    source_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    visual_kind: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    label_ja: Mapped[str | None] = mapped_column(String(512), nullable=True)
    description_ja: Mapped[str | None] = mapped_column(Text, nullable=True)
    thumbnail_asset_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    preview_kind: Mapped[str | None] = mapped_column(String(32), nullable=True)
    subcategory: Mapped[str | None] = mapped_column(String(128), nullable=True)
    tags_json: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    model_scope_json: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    related_refs_json: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
