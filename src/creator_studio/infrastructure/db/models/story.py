from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from creator_studio.infrastructure.db.base import Base


class SceneRow(Base):
    __tablename__ = "scenes"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    objective: Mapped[str] = mapped_column(Text, nullable=False, default="")
    initial_state_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class BeatRow(Base):
    __tablename__ = "beats"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    scene_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    intent: Mapped[str] = mapped_column(Text, nullable=False)
    subtext: Mapped[str] = mapped_column(Text, nullable=False, default="")
    emotion_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    action: Mapped[str] = mapped_column(Text, nullable=False, default="")
    speaker_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    state_delta_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ScriptEventRow(Base):
    __tablename__ = "script_events"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    beat_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    speaker_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    tone: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    critic_scores_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    director_plan_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)