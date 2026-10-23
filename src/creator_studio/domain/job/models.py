from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from creator_studio.domain.ids import JobId, new_id
from creator_studio.domain.timeutil import utc_now


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"


class JobKind(StrEnum):
    STUB = "stub"
    DIALOGUE_CANDIDATES = "dialogue_candidates"
    TRYON = "tryon"
    RENDER = "render"
    CSP_HANDOFF = "csp_handoff"
    RELEASE_BUILD = "release_build"
    TAG_ASSET = "tag_asset"


@dataclass
class Job:
    id: JobId
    kind: JobKind
    status: JobStatus = JobStatus.QUEUED
    payload: dict[str, Any] = field(default_factory=dict)
    progress: dict[str, Any] = field(default_factory=dict)
    attempts: int = 0
    max_attempts: int = 3
    lease_owner: str | None = None
    leased_until: datetime | None = None
    heartbeat_at: datetime | None = None
    idempotency_key: str | None = None
    external_job_ref: str | None = None
    error_message: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    @classmethod
    def create(
        cls,
        kind: JobKind,
        payload: dict[str, Any] | None = None,
        *,
        idempotency_key: str | None = None,
        max_attempts: int = 3,
    ) -> Job:
        now = utc_now()
        return cls(
            id=JobId(new_id()),
            kind=kind,
            payload=payload or {},
            idempotency_key=idempotency_key,
            max_attempts=max_attempts,
            created_at=now,
            updated_at=now,
        )