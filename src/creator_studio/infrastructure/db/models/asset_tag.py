from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from creator_studio.infrastructure.db.base import Base


class AssetTagRow(Base):
    __tablename__ = "asset_tags"
    __table_args__ = (
        UniqueConstraint(
            "asset_id",
            "tag",
            "source_model",
            "model_version",
            name="uq_asset_tag_identity",
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    asset_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    tag: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    source_model: Mapped[str] = mapped_column(String(128), nullable=False)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
