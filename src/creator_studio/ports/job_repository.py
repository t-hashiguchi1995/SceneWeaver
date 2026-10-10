from __future__ import annotations

from datetime import datetime
from typing import Protocol

from creator_studio.domain.ids import JobId
from creator_studio.domain.job import Job


class JobRepository(Protocol):
    def add(self, job: Job) -> Job: ...

    def get(self, job_id: JobId) -> Job | None: ...

    def get_by_idempotency_key(self, key: str) -> Job | None: ...

    def list(self, *, limit: int = 100) -> list[Job]: ...

    def save(self, job: Job) -> Job: ...

    def claim_next(
        self,
        *,
        worker_id: str,
        lease_until: datetime,
        now: datetime,
    ) -> Job | None: ...