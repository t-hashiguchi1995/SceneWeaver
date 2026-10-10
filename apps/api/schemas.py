from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    title: str = Field(min_length=1, max_length=512)
    content_rating: str = "general"


class ProjectOut(BaseModel):
    id: str
    title: str
    status: str
    content_rating: str
    created_at: str
    updated_at: str


class JobCreate(BaseModel):
    kind: str = "stub"
    payload: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str | None = None


class JobOut(BaseModel):
    id: str
    kind: str
    status: str
    payload: dict[str, Any]
    progress: dict[str, Any]
    attempts: int
    max_attempts: int
    lease_owner: str | None
    leased_until: str | None
    heartbeat_at: str | None
    idempotency_key: str | None
    external_job_ref: str | None
    error_message: str | None
    created_at: str
    updated_at: str


class CapabilityOut(BaseModel):
    configured: bool
    runtime_available: bool
    model_id: str | None
    detail: str = ""


class AssetOut(BaseModel):
    id: str
    sha256: str
    uri: str
    kind: str
    mime: str
    byte_size: int
    metadata: dict[str, Any]
    provenance: dict[str, Any]