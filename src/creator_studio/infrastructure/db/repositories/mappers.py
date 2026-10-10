from __future__ import annotations

from creator_studio.domain.asset import Asset, AssetKind
from creator_studio.domain.ids import AssetId, JobId, ProjectId
from creator_studio.domain.job import Job, JobKind, JobStatus
from creator_studio.domain.project import Project, ProjectStatus
from creator_studio.infrastructure.db.models import AssetRow, JobRow, ProjectRow


def project_to_row(project: Project) -> ProjectRow:
    return ProjectRow(
        id=str(project.id),
        title=project.title,
        status=project.status.value,
        content_rating=project.content_rating,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


def project_from_row(row: ProjectRow) -> Project:
    return Project(
        id=ProjectId(row.id),
        title=row.title,
        status=ProjectStatus(row.status),
        content_rating=row.content_rating,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def job_to_row(job: Job) -> JobRow:
    return JobRow(
        id=str(job.id),
        kind=job.kind.value,
        status=job.status.value,
        payload_json=job.payload,
        progress_json=job.progress,
        attempts=job.attempts,
        max_attempts=job.max_attempts,
        lease_owner=job.lease_owner,
        leased_until=job.leased_until,
        heartbeat_at=job.heartbeat_at,
        idempotency_key=job.idempotency_key,
        external_job_ref=job.external_job_ref,
        error_message=job.error_message,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


def job_from_row(row: JobRow) -> Job:
    return Job(
        id=JobId(row.id),
        kind=JobKind(row.kind),
        status=JobStatus(row.status),
        payload=dict(row.payload_json or {}),
        progress=dict(row.progress_json or {}),
        attempts=row.attempts,
        max_attempts=row.max_attempts,
        lease_owner=row.lease_owner,
        leased_until=row.leased_until,
        heartbeat_at=row.heartbeat_at,
        idempotency_key=row.idempotency_key,
        external_job_ref=row.external_job_ref,
        error_message=row.error_message,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def apply_job_to_row(job: Job, row: JobRow) -> None:
    row.kind = job.kind.value
    row.status = job.status.value
    row.payload_json = job.payload
    row.progress_json = job.progress
    row.attempts = job.attempts
    row.max_attempts = job.max_attempts
    row.lease_owner = job.lease_owner
    row.leased_until = job.leased_until
    row.heartbeat_at = job.heartbeat_at
    row.idempotency_key = job.idempotency_key
    row.external_job_ref = job.external_job_ref
    row.error_message = job.error_message
    row.updated_at = job.updated_at


def asset_to_row(asset: Asset) -> AssetRow:
    return AssetRow(
        id=str(asset.id),
        sha256=asset.sha256,
        uri=asset.uri,
        kind=asset.kind.value,
        mime=asset.mime,
        byte_size=asset.byte_size,
        metadata_json=asset.metadata,
        provenance_json=asset.provenance,
        created_at=asset.created_at,
    )


def asset_from_row(row: AssetRow) -> Asset:
    return Asset(
        id=AssetId(row.id),
        sha256=row.sha256,
        uri=row.uri,
        kind=AssetKind(row.kind),
        mime=row.mime,
        byte_size=row.byte_size,
        metadata=dict(row.metadata_json or {}),
        provenance=dict(row.provenance_json or {}),
        created_at=row.created_at,
    )