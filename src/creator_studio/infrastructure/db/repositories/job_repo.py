from __future__ import annotations

from datetime import datetime

from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session

from creator_studio.domain.ids import JobId
from creator_studio.domain.job import Job, JobStatus
from creator_studio.infrastructure.db.models import JobRow
from creator_studio.infrastructure.db.repositories.mappers import (
    apply_job_to_row,
    job_from_row,
    job_to_row,
)


class SqlAlchemyJobRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, job: Job) -> Job:
        self._session.add(job_to_row(job))
        return job

    def get(self, job_id: JobId) -> Job | None:
        row = self._session.get(JobRow, str(job_id))
        return job_from_row(row) if row else None

    def get_by_idempotency_key(self, key: str) -> Job | None:
        row = self._session.scalars(
            select(JobRow).where(JobRow.idempotency_key == key)
        ).first()
        return job_from_row(row) if row else None

    def list(self, *, limit: int = 100) -> list[Job]:
        rows = self._session.scalars(
            select(JobRow).order_by(JobRow.created_at.desc()).limit(limit)
        ).all()
        return [job_from_row(r) for r in rows]

    def save(self, job: Job) -> Job:
        row = self._session.get(JobRow, str(job.id))
        if row is None:
            return self.add(job)
        apply_job_to_row(job, row)
        return job

    def claim_next(
        self,
        *,
        worker_id: str,
        lease_until: datetime,
        now: datetime,
    ) -> Job | None:
        """Atomically claim one queued or expired-lease running job."""
        claimable = or_(
            JobRow.status == JobStatus.QUEUED.value,
            (JobRow.status == JobStatus.RUNNING.value)
            & (JobRow.leased_until.is_not(None))
            & (JobRow.leased_until < now),
        )
        candidate = self._session.scalars(
            select(JobRow).where(claimable).order_by(JobRow.created_at.asc()).limit(1)
        ).first()
        if candidate is None:
            return None

        result = self._session.execute(
            update(JobRow)
            .where(JobRow.id == candidate.id, claimable)
            .values(
                status=JobStatus.RUNNING.value,
                lease_owner=worker_id,
                leased_until=lease_until,
                heartbeat_at=now,
                attempts=candidate.attempts + 1,
                updated_at=now,
            )
        )
        if result.rowcount != 1:
            return None
        self._session.flush()
        row = self._session.get(JobRow, candidate.id)
        assert row is not None
        return job_from_row(row)