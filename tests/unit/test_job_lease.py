from __future__ import annotations

from datetime import timedelta

from creator_studio.application.jobs.manage_jobs import EnqueueJobCommand
from creator_studio.domain.job import JobKind, JobStatus
from creator_studio.domain.timeutil import utc_now
from creator_studio.infrastructure.container import Container


def test_atomic_claim_and_stub_complete(container: Container) -> None:
    enqueue = container.enqueue_job()
    job = enqueue.execute(EnqueueJobCommand(kind=JobKind.STUB, payload={"n": 1}))
    assert job.status == JobStatus.QUEUED.value

    runner = container.claim_runner()
    claimed = runner.claim()
    assert claimed is not None
    assert claimed.id == job.id
    assert claimed.status == JobStatus.RUNNING.value
    assert claimed.lease_owner == container.settings.worker_id
    assert claimed.attempts == 1

    # second claim finds nothing
    assert runner.claim() is None

    done = runner.complete_stub(claimed.id)
    assert done.status == JobStatus.SUCCEEDED.value
    assert done.progress["percent"] == 100


def test_expired_lease_can_be_reclaimed(container: Container) -> None:
    enqueue = container.enqueue_job()
    job = enqueue.execute(EnqueueJobCommand(kind=JobKind.STUB))
    runner = container.claim_runner()
    claimed = runner.claim()
    assert claimed is not None

    # force expire lease
    from creator_studio.domain.ids import JobId

    with container.uow() as uow:
        entity = uow.jobs.get(JobId(claimed.id))
        assert entity is not None
        entity.leased_until = utc_now() - timedelta(seconds=5)
        uow.jobs.save(entity)
        uow.commit()

    reclaimed = runner.claim()
    assert reclaimed is not None
    assert reclaimed.id == job.id
    assert reclaimed.attempts == 2


def test_idempotency_key_returns_same_job(container: Container) -> None:
    enqueue = container.enqueue_job()
    a = enqueue.execute(
        EnqueueJobCommand(kind=JobKind.STUB, idempotency_key="once-1", payload={"x": 1})
    )
    b = enqueue.execute(
        EnqueueJobCommand(kind=JobKind.STUB, idempotency_key="once-1", payload={"x": 2})
    )
    assert a.id == b.id