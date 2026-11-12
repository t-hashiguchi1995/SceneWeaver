from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from sqlalchemy.exc import IntegrityError

from creator_studio.domain.ids import JobId
from creator_studio.domain.job import Job, JobKind, JobStatus
from creator_studio.domain.shot.execution_snapshot import (
    ExecutionSnapshot,
    IdempotencyAction,
    decide_idempotency,
)
from creator_studio.domain.timeutil import utc_now
from creator_studio.ports.unit_of_work import UnitOfWork


class FencingError(RuntimeError):
    """The job has been claimed by a newer attempt."""


class IdempotencyConflictError(RuntimeError):
    http_status = 409

    def __init__(self, message: str, *, existing_job_id: str | None = None) -> None:
        super().__init__(message)
        self.existing_job_id = existing_job_id


@dataclass
class JobDTO:
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
    snapshot_hash: str | None
    snapshot_schema_version: int | None
    execution_snapshot: dict | None
    submission_correlation_key: str | None = None
    submission_provider: str | None = None
    submission_attempt: int | None = None
    submission_intended_at: str | None = None


def to_dto(job: Job) -> JobDTO:
    return JobDTO(
        submission_correlation_key=job.submission_correlation_key,
        submission_provider=job.submission_provider,
        submission_attempt=job.submission_attempt,
        submission_intended_at=(
            job.submission_intended_at.isoformat() if job.submission_intended_at else None
        ),
        snapshot_hash=job.snapshot_hash,
        snapshot_schema_version=job.snapshot_schema_version,
        execution_snapshot=job.execution_snapshot.to_dict() if job.execution_snapshot else None,
        id=str(job.id),
        kind=job.kind.value,
        status=job.status.value,
        payload=job.payload,
        progress=job.progress,
        attempts=job.attempts,
        max_attempts=job.max_attempts,
        lease_owner=job.lease_owner,
        leased_until=job.leased_until.isoformat() if job.leased_until else None,
        heartbeat_at=job.heartbeat_at.isoformat() if job.heartbeat_at else None,
        idempotency_key=job.idempotency_key,
        external_job_ref=job.external_job_ref,
        error_message=job.error_message,
        created_at=job.created_at.isoformat(),
        updated_at=job.updated_at.isoformat(),
    )


@dataclass
class EnqueueJobCommand:
    kind: JobKind
    payload: dict[str, Any] | None = None
    idempotency_key: str | None = None
    max_attempts: int = 3
    execution_snapshot: ExecutionSnapshot | None = None


class EnqueueJob:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, cmd: EnqueueJobCommand) -> JobDTO:
        with self._uow as uow:
            if cmd.idempotency_key:
                existing = uow.jobs.get_by_idempotency_key(cmd.idempotency_key)
                if existing:
                    return self._existing_dto(existing, cmd.execution_snapshot)
            job = Job.create(
                cmd.kind,
                cmd.payload,
                idempotency_key=cmd.idempotency_key,
                max_attempts=cmd.max_attempts,
                execution_snapshot=cmd.execution_snapshot,
            )
            try:
                uow.jobs.add(job)
                uow.commit()
            except IntegrityError:
                uow.rollback()
                if cmd.idempotency_key:
                    existing = uow.jobs.get_by_idempotency_key(cmd.idempotency_key)
                    if existing is not None:
                        return self._existing_dto(existing, cmd.execution_snapshot)
                raise
            return to_dto(job)

    @staticmethod
    def _existing_dto(existing: Job, incoming: ExecutionSnapshot | None) -> JobDTO:
        if incoming is None:
            return to_dto(existing)
        if existing.execution_snapshot is not None:
            decision = decide_idempotency(str(existing.id), existing.execution_snapshot, incoming)
            if decision.action == IdempotencyAction.REUSE_EXISTING:
                return to_dto(existing)
        raise IdempotencyConflictError(
            "Idempotency key already belongs to a job with a different or missing snapshot",
            existing_job_id=str(existing.id),
        )


class ListJobs:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, *, limit: int = 100) -> list[JobDTO]:
        with self._uow as uow:
            return [to_dto(j) for j in uow.jobs.list(limit=limit)]


class GetJob:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, job_id: str) -> JobDTO | None:
        with self._uow as uow:
            job = uow.jobs.get(JobId(job_id))
            return to_dto(job) if job else None


class ClaimAndRunStubJob:
    """Worker helper: claim next job and complete stub jobs."""

    def __init__(self, uow: UnitOfWork, *, worker_id: str, lease_seconds: int) -> None:
        self._uow = uow
        self._worker_id = worker_id
        self._lease_seconds = lease_seconds

    def claim(self) -> JobDTO | None:
        now = utc_now()
        lease_until = now + timedelta(seconds=self._lease_seconds)
        with self._uow as uow:
            job = uow.jobs.claim_next(
                worker_id=self._worker_id,
                lease_until=lease_until,
                now=now,
            )
            if job is None:
                uow.commit()
                return None
            uow.commit()
            return to_dto(job)

    def heartbeat(self, job_id: str, *, expected_attempts: int | None = None) -> None:
        now = utc_now()
        with self._uow as uow:
            job = uow.jobs.get(JobId(job_id))
            if job is None:
                return
            if expected_attempts is not None and job.attempts != expected_attempts:
                raise FencingError("job claim generation mismatch")
            if job.lease_owner != self._worker_id:
                return
            job.heartbeat_at = now
            job.leased_until = now + timedelta(seconds=self._lease_seconds)
            job.updated_at = now
            uow.jobs.save(job)
            uow.commit()

    def complete_stub(self, job_id: str) -> JobDTO:
        now = utc_now()
        with self._uow as uow:
            job = uow.jobs.get(JobId(job_id))
            if job is None:
                raise ValueError("job not found")
            if job.kind != JobKind.STUB:
                raise ValueError(f"unsupported kind for stub runner: {job.kind}")
            job.progress = {"percent": 100, "message": "stub completed"}
            job.status = JobStatus.SUCCEEDED
            job.lease_owner = None
            job.leased_until = None
            job.updated_at = now
            uow.jobs.save(job)
            uow.commit()
            return to_dto(job)

    def succeed(
        self,
        job_id: str,
        *,
        progress: dict[str, Any] | None = None,
        expected_attempts: int | None = None,
    ) -> JobDTO:
        now = utc_now()
        with self._uow as uow:
            job = uow.jobs.get(JobId(job_id))
            if job is None:
                raise ValueError("job not found")
            if expected_attempts is not None and job.attempts != expected_attempts:
                raise FencingError("job claim generation mismatch")
            job.progress = progress or {"percent": 100}
            job.status = JobStatus.SUCCEEDED
            job.lease_owner = None
            job.leased_until = None
            job.error_message = None
            job.updated_at = now
            uow.jobs.save(job)
            uow.commit()
            return to_dto(job)

    def fail(
        self, job_id: str, message: str, *, expected_attempts: int | None = None
    ) -> JobDTO:
        now = utc_now()
        with self._uow as uow:
            job = uow.jobs.get(JobId(job_id))
            if job is None:
                raise ValueError("job not found")
            if expected_attempts is not None and job.attempts != expected_attempts:
                raise FencingError("job claim generation mismatch")
            if job.attempts >= job.max_attempts:
                job.status = JobStatus.FAILED
            else:
                job.status = JobStatus.QUEUED
                job.lease_owner = None
                job.leased_until = None
            job.error_message = message
            job.updated_at = now
            uow.jobs.save(job)
            uow.commit()
            return to_dto(job)