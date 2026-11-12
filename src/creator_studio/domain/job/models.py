from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from creator_studio.domain.ids import JobId, new_id
from creator_studio.domain.job.submission import SubmissionIntent
from creator_studio.domain.shot.execution_snapshot import ExecutionSnapshot
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

    execution_snapshot: ExecutionSnapshot | None = None

    submission_intent: SubmissionIntent | None = None

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "execution_snapshot":
            existing = self.__dict__.get(name)
            if existing is not None:
                if value is None or value.snapshot_hash != existing.snapshot_hash:
                    raise ValueError("execution_snapshot is frozen after enqueue")
                return
        if name == "submission_intent":
            existing = self.__dict__.get(name)
            if existing is not None:
                if value is None or value.correlation_key != existing.correlation_key:
                    raise ValueError("submission_intent is frozen after recording")
                return
        object.__setattr__(self, name, value)

    @property
    def submission_correlation_key(self) -> str | None:
        return self.submission_intent.correlation_key if self.submission_intent else None

    @property
    def submission_provider(self) -> str | None:
        return self.submission_intent.provider if self.submission_intent else None

    @property
    def submission_attempt(self) -> int | None:
        return self.submission_intent.attempt if self.submission_intent else None

    @property
    def submission_intended_at(self) -> datetime | None:
        return self.submission_intent.intended_at if self.submission_intent else None

    @property
    def snapshot_hash(self) -> str | None:
        return self.execution_snapshot.snapshot_hash if self.execution_snapshot else None

    @property
    def snapshot_schema_version(self) -> int | None:
        return self.execution_snapshot.schema_version if self.execution_snapshot else None

    @classmethod
    def create(
        cls,
        kind: JobKind,
        payload: dict[str, Any] | None = None,
        *,
        idempotency_key: str | None = None,
        max_attempts: int = 3,
        execution_snapshot: ExecutionSnapshot | None = None,
    ) -> Job:
        now = utc_now()
        return cls(
            id=JobId(new_id()),
            kind=kind,
            payload=payload or {},
            idempotency_key=idempotency_key,
            max_attempts=max_attempts,
            execution_snapshot=execution_snapshot,
            created_at=now,
            updated_at=now,
        )
