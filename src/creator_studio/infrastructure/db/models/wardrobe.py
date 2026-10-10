from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from creator_studio.infrastructure.db.base import Base


class MarketplaceItemRow(Base):
    __tablename__ = "marketplace_items"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    region: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    style_tags_json: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    season_tags_json: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    colors_json: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    garment_description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    canonical_plate_asset_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    verification_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    search_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class OutfitProfileRow(Base):
    __tablename__ = "outfit_profiles"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    character_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    marketplace_item_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    semantic_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    references_json: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class TryOnSessionRow(Base):
    __tablename__ = "tryon_sessions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    character_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    outfit_profile_id: Mapped[str] = mapped_column(String(32), nullable=False)
    source_asset_id: Mapped[str] = mapped_column(String(32), nullable=False)
    plate_asset_id: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    candidate_asset_ids_json: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    adopted_asset_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)