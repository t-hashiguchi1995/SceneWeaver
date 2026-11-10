from __future__ import annotations

from creator_studio.domain.asset import Asset, AssetKind
from creator_studio.domain.camera.models import (
    CameraAnchor,
    CameraQCReport,
    CameraRig,
    ShotCameraBinding,
)
from creator_studio.domain.ids import AssetId, JobId, ProjectId, ShotId
from creator_studio.domain.job import Job, JobKind, JobStatus
from creator_studio.domain.project import Project, ProjectStatus
from creator_studio.infrastructure.db.models import AssetRow, JobRow, ProjectRow
from creator_studio.infrastructure.db.models.camera import (
    CameraAnchorRow,
    CameraQCReportRow,
    CameraRigRow,
    ShotCameraBindingRow,
)


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


def camera_rig_to_row(value: CameraRig) -> CameraRigRow:
    return CameraRigRow(
        id=value.id,
        project_id=value.project_id,
        name=value.name,
        frame_json=value.frame,
        revision=value.revision,
        view_json=value.view,
        anchor_asset_id=value.anchor_asset_id,
        background_mask_asset_id=value.background_mask_asset_id,
        preservation_mode=value.preservation_mode,
        camera_device_visibility=value.camera_device_visibility,
        face_policy=value.face_policy,
        qc_profile_id=value.qc_profile_id,
        status=value.status,
        created_at=value.created_at,
        updated_at=value.updated_at,
    )


def camera_rig_from_row(row: CameraRigRow) -> CameraRig:
    return CameraRig(
        id=row.id,
        project_id=ProjectId(row.project_id),
        name=row.name,
        frame=row.frame_json,
        revision=row.revision,
        view=row.view_json,
        anchor_asset_id=row.anchor_asset_id,
        background_mask_asset_id=row.background_mask_asset_id,
        preservation_mode=row.preservation_mode,
        camera_device_visibility=row.camera_device_visibility,
        face_policy=row.face_policy,
        qc_profile_id=row.qc_profile_id,
        status=row.status,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def camera_anchor_to_row(value: CameraAnchor) -> CameraAnchorRow:
    return CameraAnchorRow(
        id=value.id,
        rig_id=value.rig_id,
        revision=value.revision,
        image_asset_id=value.image_asset_id,
        bg_mask_asset_id=value.bg_mask_asset_id,
        sha256=value.sha256,
        face_visibility=value.face_visibility,
        face_check_json=value.face_check,
        created_at=value.created_at,
    )


def camera_anchor_from_row(row: CameraAnchorRow) -> CameraAnchor:
    return CameraAnchor(
        id=row.id,
        rig_id=row.rig_id,
        revision=row.revision,
        image_asset_id=row.image_asset_id,
        bg_mask_asset_id=row.bg_mask_asset_id,
        sha256=row.sha256,
        face_visibility=row.face_visibility,
        face_check=row.face_check_json,
        created_at=row.created_at,
    )


def shot_camera_binding_to_row(value: ShotCameraBinding) -> ShotCameraBindingRow:
    return ShotCameraBindingRow(
        id=value.id,
        shot_id=value.shot_id,
        rig_id=value.rig_id,
        rig_revision=value.rig_revision,
        anchor_asset_sha256=value.anchor_asset_sha256,
        face_policy=value.face_policy,
        subject_motion=value.subject_motion,
        subject_distance_class=value.subject_distance_class,
        edit_mask_asset_id=value.edit_mask_asset_id,
        pose_asset_id=value.pose_asset_id,
        created_at=value.created_at,
        updated_at=value.updated_at,
    )


def shot_camera_binding_from_row(row: ShotCameraBindingRow) -> ShotCameraBinding:
    return ShotCameraBinding(
        id=row.id,
        shot_id=ShotId(row.shot_id),
        rig_id=row.rig_id,
        rig_revision=row.rig_revision,
        anchor_asset_sha256=row.anchor_asset_sha256,
        face_policy=row.face_policy,
        subject_motion=row.subject_motion,
        subject_distance_class=row.subject_distance_class,
        edit_mask_asset_id=row.edit_mask_asset_id,
        pose_asset_id=row.pose_asset_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def camera_qc_report_to_row(value: CameraQCReport) -> CameraQCReportRow:
    return CameraQCReportRow(
        id=value.id,
        attempt_id=value.attempt_id,
        candidate_asset_id=value.candidate_asset_id,
        scores_json=value.scores,
        decision=value.decision,
        reason_codes_json=value.reason_codes,
        version=value.version,
        created_at=value.created_at,
    )


def camera_qc_report_from_row(row: CameraQCReportRow) -> CameraQCReport:
    return CameraQCReport(
        id=row.id,
        attempt_id=row.attempt_id,
        candidate_asset_id=row.candidate_asset_id,
        scores=row.scores_json,
        decision=row.decision,
        reason_codes=row.reason_codes_json,
        version=row.version,
        created_at=row.created_at,
    )
