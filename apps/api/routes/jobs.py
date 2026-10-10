from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Query
from sse_starlette.sse import EventSourceResponse

from apps.api.deps import container
from apps.api.schemas import JobCreate, JobOut
from creator_studio.application.jobs.manage_jobs import EnqueueJobCommand
from creator_studio.domain.job import JobKind
from creator_studio.infrastructure.container import Container

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


def _to_out(dto: object) -> JobOut:
    return JobOut(**dto.__dict__)  # type: ignore[arg-type]


@router.post("", response_model=JobOut)
def enqueue_job(body: JobCreate, c: Container = Depends(container)) -> JobOut:
    try:
        kind = JobKind(body.kind)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"unknown job kind: {body.kind}") from e
    dto = c.enqueue_job().execute(
        EnqueueJobCommand(
            kind=kind,
            payload=body.payload,
            idempotency_key=body.idempotency_key,
        )
    )
    return _to_out(dto)


@router.get("", response_model=list[JobOut])
def list_jobs(
    limit: int = Query(default=100, ge=1, le=500),
    c: Container = Depends(container),
) -> list[JobOut]:
    return [_to_out(j) for j in c.list_jobs().execute(limit=limit)]


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: str, c: Container = Depends(container)) -> JobOut:
    dto = c.get_job().execute(job_id)
    if dto is None:
        raise HTTPException(status_code=404, detail="job not found")
    return _to_out(dto)


@router.get("/{job_id}/events")
async def job_events(job_id: str, c: Container = Depends(container)) -> EventSourceResponse:
    async def gen() -> AsyncIterator[dict[str, str]]:
        last_payload: str | None = None
        while True:
            dto = c.get_job().execute(job_id)
            if dto is None:
                yield {"event": "error", "data": json.dumps({"detail": "job not found"})}
                break
            payload = json.dumps(dto.__dict__)
            if payload != last_payload:
                yield {"event": "job", "data": payload}
                last_payload = payload
            if dto.status in {"succeeded", "failed", "cancelled"}:
                yield {"event": "done", "data": payload}
                break
            await asyncio.sleep(0.5)

    return EventSourceResponse(gen())