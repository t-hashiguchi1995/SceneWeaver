from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from creator_studio.infrastructure.db.base import Base


class AssetRow(Base):
    __tablename__ = "assets"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    uri: Mapped[str] = mapped_column(String(1024), nullable=False)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    mime: Mapped[str] = mapped_column(String(128), nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    provenance_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AssetLinkRow(Base):
    __tablename__ = "asset_links"
    __table_args__ = (
        UniqueConstraint("asset_id", "entity_type", "entity_id", "role", name="uq_asset_link"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    asset_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(32), nullable=False)
    role: Mapped[str] = mapped_column(String(64), nullable=False)