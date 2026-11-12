"""Submission transaction boundary and restart reconciliation contract."""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from creator_studio.application.jobs.manage_jobs import FencingError, JobDTO, to_dto
from creator_studio.domain.ids import JobId
from creator_studio.domain.job import Job, JobStatus, SubmissionIntent, make_correlation_key
from creator_studio.domain.timeutil import utc_now
from creator_studio.ports.unit_of_work import UnitOfWork


class SubmissionIntentMissingError(RuntimeError):
    """A prompt reference requires a previously committed intent."""


class SubmissionAlreadyRecordedError(RuntimeError):
    """The external prompt reference is already recorded."""


class SubmissionAttemptConflictError(RuntimeError):
    """An earlier attempt's intent must be reconciled first."""


class SubmissionClient(Protocol):
    def submit(self, *, correlation_key: str) -> str: ...

    def lookup_prompt_id(self, *, correlation_key: str) -> str | None: ...


class ReconcileOutcome(StrEnum):
    RECONNECTED = "reconnected"
    BLOCKED = "blocked"
    ALREADY_RECORDED = "already_recorded"
    NOT_SUBMITTED = "not_submitted"


@dataclass(frozen=True)
class ReconcileResult:
    outcome: ReconcileOutcome
    job: JobDTO


class JobSubmissionService:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    @staticmethod
    def _load(uow: UnitOfWork, job_id: str, expected_attempts: int | None) -> Job:
        job = uow.jobs.get(JobId(job_id))
        if job is None:
            raise ValueError("job not found")
        if expected_attempts is not None and job.attempts != expected_attempts:
            raise FencingError("job claim generation mismatch")
        return job

    def begin_submission(self, job_id: str, *, expected_attempts: int | None = None) -> JobDTO:
        with self._uow as uow:
            job = self._load(uow, job_id, expected_attempts)
            if job.external_job_ref:
                raise SubmissionAlreadyRecordedError("external prompt reference already recorded")
            if job.submission_intent is not None:
                if job.submission_intent.attempt != job.attempts:
                    raise SubmissionAttemptConflictError(
                        "submission intent exists for a different attempt; reconcile it first"
                    )
                return to_dto(job)
            job.submission_intent = SubmissionIntent(
                job_id=str(job.id),
                attempt=job.attempts,
                correlation_key=make_correlation_key(str(job.id), job.attempts),
                snapshot_hash=job.snapshot_hash,
                intended_at=utc_now(),
            )
            job.updated_at = utc_now()
            uow.jobs.save(job)
            uow.commit()
            return to_dto(job)

    def record_prompt_id(
        self, job_id: str, prompt_id: str, *, expected_attempts: int | None = None
    ) -> JobDTO:
        if not isinstance(prompt_id, str) or not prompt_id.strip():
            raise ValueError("prompt_id must be non-empty")
        with self._uow as uow:
            job = self._load(uow, job_id, expected_attempts)
            if job.submission_intent is None:
                raise SubmissionIntentMissingError("persist a submission intent before recording")
            job.external_job_ref = prompt_id
            job.updated_at = utc_now()
            uow.jobs.save(job)
            uow.commit()
            return to_dto(job)

    def submit(
        self, job_id: str, client: SubmissionClient, *, expected_attempts: int | None = None
    ) -> JobDTO:
        dto = self.begin_submission(job_id, expected_attempts=expected_attempts)
        assert dto.submission_correlation_key is not None
        prompt_id = client.submit(correlation_key=dto.submission_correlation_key)
        return self.record_prompt_id(job_id, prompt_id, expected_attempts=expected_attempts)

    def reconcile(
        self, job_id: str, client: SubmissionClient, *, expected_attempts: int | None = None
    ) -> ReconcileResult:
        with self._uow as uow:
            job = self._load(uow, job_id, expected_attempts)
            if job.external_job_ref:
                return ReconcileResult(ReconcileOutcome.ALREADY_RECORDED, to_dto(job))
            if job.submission_intent is None:
                return ReconcileResult(ReconcileOutcome.NOT_SUBMITTED, to_dto(job))
            key = job.submission_intent.correlation_key
            prompt_id = client.lookup_prompt_id(correlation_key=key)
            if prompt_id is not None:
                job.external_job_ref = prompt_id
                job.progress = {**job.progress, "submission_reconciled": True}
                outcome = ReconcileOutcome.RECONNECTED
            else:
                job.status = JobStatus.BLOCKED
                job.lease_owner = None
                job.leased_until = None
                job.error_message = (
                    f"Submission outcome is unknown for {key}; automatic resubmit is disabled"
                )
                outcome = ReconcileOutcome.BLOCKED
            job.updated_at = utc_now()
            uow.jobs.save(job)
            uow.commit()
            return ReconcileResult(outcome, to_dto(job))
