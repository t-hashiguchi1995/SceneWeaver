from __future__ import annotations

from datetime import timedelta

import pytest

from creator_studio.application.jobs.manage_jobs import EnqueueJobCommand, FencingError
from creator_studio.domain.ids import JobId
from creator_studio.domain.job import JobKind, JobStatus
from creator_studio.domain.timeutil import utc_now
from creator_studio.infrastructure.container import Container


@pytest.mark.parametrize("status", [JobStatus.QUEUED, JobStatus.RUNNING])
def test_exhausted_job_is_skipped(container: Container, status: JobStatus) -> None:
    exhausted = container.enqueue_job().execute(EnqueueJobCommand(kind=JobKind.STUB))
    with container.uow() as uow:
        job = uow.jobs.get(JobId(exhausted.id))
        assert job is not None
        job.attempts = job.max_attempts
        job.status = status
        job.leased_until = utc_now() - timedelta(seconds=5)
        job.created_at = utc_now() - timedelta(days=1)
        uow.jobs.save(job)
        uow.commit()

    runner = container.claim_runner()
    assert runner.claim() is None
    eligible = container.enqueue_job().execute(EnqueueJobCommand(kind=JobKind.STUB))
    claimed = runner.claim()
    assert claimed is not None
    assert claimed.id == eligible.id
    assert claimed.attempts == 1
    unchanged = container.get_job().execute(exhausted.id)
    assert unchanged is not None
    assert unchanged.status == status.value
    assert unchanged.attempts == exhausted.max_attempts


@pytest.mark.parametrize("fenced", [False, True])
def test_matching_attempt_and_legacy_operations(container: Container, fenced: bool) -> None:
    container.enqueue_job().execute(EnqueueJobCommand(kind=JobKind.STUB))
    runner = container.claim_runner()
    claimed = runner.claim()
    assert claimed is not None
    with container.uow() as uow:
        job = uow.jobs.get(JobId(claimed.id))
        assert job is not None
        job.heartbeat_at = utc_now() - timedelta(seconds=20)
        job.leased_until = utc_now() - timedelta(seconds=10)
        uow.jobs.save(job)
        uow.commit()
    before = container.get_job().execute(claimed.id)
    assert before is not None
    kwargs = {"expected_attempts": claimed.attempts} if fenced else {}
    runner.heartbeat(claimed.id, **kwargs)
    after = container.get_job().execute(claimed.id)
    assert after is not None
    assert after.heartbeat_at > before.heartbeat_at
    assert after.leased_until > before.leased_until

    failed = runner.fail(claimed.id, "retry me", **kwargs)
    assert failed.status == JobStatus.QUEUED.value
    assert failed.error_message == "retry me"
    assert failed.lease_owner is None
    assert failed.leased_until is None
    reclaimed = runner.claim()
    assert reclaimed is not None
    assert reclaimed.attempts == claimed.attempts + 1
    kwargs = {"expected_attempts": reclaimed.attempts} if fenced else {}
    done = runner.succeed(reclaimed.id, progress={"percent": 100, "ok": True}, **kwargs)
    assert done.status == JobStatus.SUCCEEDED.value
    assert done.progress == {"percent": 100, "ok": True}
    assert done.error_message is None


@pytest.mark.parametrize("operation", ["heartbeat", "succeed", "fail"])
@pytest.mark.parametrize("other_owner", [False, True])
def test_stale_attempt_does_not_mutate(
    container: Container, operation: str, other_owner: bool
) -> None:
    container.enqueue_job().execute(EnqueueJobCommand(kind=JobKind.STUB))
    runner = container.claim_runner()
    claimed = runner.claim()
    assert claimed is not None
    with container.uow() as uow:
        job = uow.jobs.get(JobId(claimed.id))
        assert job is not None
        job.error_message = "existing error"
        if other_owner:
            job.lease_owner = "another-worker"
        uow.jobs.save(job)
        uow.commit()
    before = container.get_job().execute(claimed.id)
    assert before is not None
    with pytest.raises(FencingError):
        if operation == "heartbeat":
            runner.heartbeat(claimed.id, expected_attempts=claimed.attempts - 1)
        elif operation == "succeed":
            runner.succeed(claimed.id, expected_attempts=claimed.attempts - 1)
        else:
            runner.fail(claimed.id, "stale error", expected_attempts=claimed.attempts - 1)
    after = container.get_job().execute(claimed.id)
    assert after == before
    assert after.status == JobStatus.RUNNING.value


def test_legacy_heartbeat_ignores_other_owner(container: Container) -> None:
    container.enqueue_job().execute(EnqueueJobCommand(kind=JobKind.STUB))
    runner = container.claim_runner()
    claimed = runner.claim()
    assert claimed is not None
    with container.uow() as uow:
        job = uow.jobs.get(JobId(claimed.id))
        assert job is not None
        job.lease_owner = "another-worker"
        uow.jobs.save(job)
        uow.commit()
    before = container.get_job().execute(claimed.id)
    runner.heartbeat(claimed.id)
    assert container.get_job().execute(claimed.id) == before


@pytest.mark.parametrize("fenced", [False, True])
def test_fail_at_attempt_limit(container: Container, fenced: bool) -> None:
    container.enqueue_job().execute(EnqueueJobCommand(kind=JobKind.STUB, max_attempts=1))
    runner = container.claim_runner()
    claimed = runner.claim()
    assert claimed is not None
    kwargs = {"expected_attempts": claimed.attempts} if fenced else {}
    failed = runner.fail(claimed.id, "exhausted", **kwargs)
    assert failed.status == JobStatus.FAILED.value
    assert failed.error_message == "exhausted"
