from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from creator_studio.infrastructure.db.base import Base


class CharacterRow(Base):
    __tablename__ = "characters"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(256), nullable=False)
    visual_identity_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    persona_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)