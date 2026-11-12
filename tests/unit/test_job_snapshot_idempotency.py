from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import UniqueConstraint
from sqlalchemy.exc import IntegrityError

from apps.api.deps import container as container_dep
from apps.api.main import app
from creator_studio.application.jobs.manage_jobs import EnqueueJobCommand, IdempotencyConflictError
from creator_studio.domain.ids import JobId
from creator_studio.domain.job import Job, JobKind
from creator_studio.domain.shot.execution_snapshot import (
    AssetRef,
    CandidateSpec,
    ControlPass,
    EnvironmentSpec,
    ExecutionSnapshot,
    GenerationParams,
    ModelArtifactRef,
)
from creator_studio.infrastructure.db.models.job import JobRow
from creator_studio.infrastructure.db.repositories.job_repo import SqlAlchemyJobRepository
from creator_studio.infrastructure.db.repositories.mappers import job_from_row, job_to_row


def make_snapshot(seed: int = 42) -> ExecutionSnapshot:
    model = ModelArtifactRef(content_hash="a" * 64)
    return ExecutionSnapshot(
        shot_id="shot-1", shot_revision=1,
        source=AssetRef("source", "b" * 64), depth=AssetRef("depth", "c" * 64),
        control_passes=(ControlPass("depth", 0.8),),
        generation=GenerationParams("夜の街", "", seed, 20, 7, 0.6, "euler", "normal"),
        candidates=CandidateSpec(2, "repeat_latent_batch"),
        environment=EnvironmentSpec("template", "e" * 64, model, model, model),
    )


def command(snapshot=None, key="key") -> EnqueueJobCommand:
    return EnqueueJobCommand(JobKind.STUB, idempotency_key=key, execution_snapshot=snapshot)


def test_reuse_and_conflict(container):
    first = container.enqueue_job().execute(command(make_snapshot()))
    assert container.enqueue_job().execute(command(make_snapshot())).id == first.id
    assert len(container.list_jobs().execute()) == 1
    with pytest.raises(IdempotencyConflictError) as exc:
        container.enqueue_job().execute(command(make_snapshot(43)))
    assert exc.value.http_status == 409
    assert exc.value.existing_job_id == first.id


def test_snapshot_frozen_and_persisted(container):
    snapshot = make_snapshot()
    dto = container.enqueue_job().execute(command(snapshot))
    assert dto.snapshot_hash == snapshot.snapshot_hash
    assert dto.snapshot_schema_version == snapshot.schema_version
    assert dto.execution_snapshot == snapshot.to_dict()
    with container.uow() as uow:
        job = uow.jobs.get(JobId(dto.id))
        assert job.execution_snapshot == snapshot
        job.execution_snapshot = make_snapshot()
        for value in (None, make_snapshot(43)):
            with pytest.raises(ValueError, match="frozen"):
                job.execution_snapshot = value
        job.progress = {"percent": 10}
        uow.jobs.save(job)
        uow.commit()
        object.__setattr__(job, "execution_snapshot", make_snapshot(43))
        with pytest.raises(ValueError, match="frozen"):
            uow.jobs.save(job)
    restored = container.get_job().execute(dto.id)
    assert restored.snapshot_hash == dto.snapshot_hash
    assert restored.execution_snapshot == dto.execution_snapshot
    assert restored.progress == {"percent": 10}


def test_unique_constraint_and_direct_insert(container):
    table = JobRow.__table__
    assert any(
        isinstance(c, UniqueConstraint) and list(c.columns.keys()) == ["idempotency_key"]
        for c in table.constraints
    ) or any(i.unique and list(i.columns.keys()) == ["idempotency_key"] for i in table.indexes)
    with pytest.raises(IntegrityError), container.uow() as uow:
        uow.jobs.add(Job.create(JobKind.STUB, idempotency_key="duplicate"))
        uow.jobs.add(Job.create(JobKind.STUB, idempotency_key="duplicate"))
        uow.commit()


@pytest.mark.parametrize("existing_seed,incoming_seed", [
    (42, 42), (42, 43), (42, None), (None, 42), (None, None),
])
def test_commit_race(container, monkeypatch, existing_seed, incoming_seed):
    existing_snapshot = make_snapshot(existing_seed) if existing_seed is not None else None
    incoming = make_snapshot(incoming_seed) if incoming_seed is not None else None
    first = container.enqueue_job().execute(command(existing_snapshot))
    original = SqlAlchemyJobRepository.get_by_idempotency_key
    calls = 0

    def miss_first(self, key):
        nonlocal calls
        calls += 1
        return None if calls == 1 else original(self, key)

    monkeypatch.setattr(SqlAlchemyJobRepository, "get_by_idempotency_key", miss_first)
    if incoming_seed is not None and incoming_seed != existing_seed:
        with pytest.raises(IdempotencyConflictError) as exc:
            container.enqueue_job().execute(command(incoming))
        assert exc.value.existing_job_id == first.id
    else:
        assert container.enqueue_job().execute(command(incoming)).id == first.id
    assert calls == 2
    assert len(container.list_jobs().execute()) == 1


def test_legacy_and_mixed_cases(container):
    legacy = container.enqueue_job().execute(command())
    assert legacy.execution_snapshot is None
    assert container.enqueue_job().execute(command()).id == legacy.id
    with pytest.raises(IdempotencyConflictError):
        container.enqueue_job().execute(command(make_snapshot()))
    aware = container.enqueue_job().execute(command(make_snapshot(), "aware"))
    assert container.enqueue_job().execute(command(None, "aware")).id == aware.id
    first = container.enqueue_job().execute(command(make_snapshot(), None))
    second = container.enqueue_job().execute(command(make_snapshot(), None))
    assert first.id != second.id
    assert container.enqueue_job().execute(command(None, None)).execution_snapshot is None


@pytest.mark.parametrize("corruption", ["json", "shape", "hash"])
def test_corrupt_snapshot_rejected(corruption):
    row = job_to_row(Job.create(JobKind.STUB, execution_snapshot=make_snapshot()))
    if corruption == "json":
        row.snapshot_json = "{"
    elif corruption == "shape":
        row.snapshot_json = "{}"
    else:
        row.snapshot_hash = "f" * 64
    with pytest.raises(ValueError, match="corrupt"):
        job_from_row(row)


@pytest.mark.skip(reason="TestClient hangs in this sandbox, including with an empty FastAPI app")
def test_route_snapshot_idempotency(container):
    app.dependency_overrides[container_dep] = lambda: container
    try:
        with TestClient(app) as client:
            body = {"idempotency_key": "api", "execution_snapshot": make_snapshot().to_dict()}
            first = client.post("/api/v1/jobs", json=body)
            second = client.post("/api/v1/jobs", json=body)
            assert first.status_code == second.status_code == 200
            assert first.json()["id"] == second.json()["id"]
            assert first.json()["snapshot_hash"] == make_snapshot().snapshot_hash
            body["execution_snapshot"] = make_snapshot(43).to_dict()
            assert client.post("/api/v1/jobs", json=body).status_code == 409
            body["execution_snapshot"] = {}
            assert client.post("/api/v1/jobs", json=body).status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_route_handler_snapshot_idempotency(container):
    from fastapi import HTTPException

    from apps.api.routes.jobs import enqueue_job
    from apps.api.schemas import JobCreate

    body = JobCreate(idempotency_key="handler", execution_snapshot=make_snapshot().to_dict())
    first = enqueue_job(body, container)
    assert enqueue_job(body, container).id == first.id
    assert first.snapshot_hash == make_snapshot().snapshot_hash
    body.execution_snapshot = make_snapshot(43).to_dict()
    with pytest.raises(HTTPException) as exc:
        enqueue_job(body, container)
    assert exc.value.status_code == 409
    body.execution_snapshot = {}
    with pytest.raises(HTTPException) as exc:
        enqueue_job(body, container)
    assert exc.value.status_code == 422
