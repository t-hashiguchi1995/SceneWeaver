from datetime import datetime

from sqlalchemy import DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from creator_studio.infrastructure.db.base import Base


class CameraRigRow(Base):
    __tablename__ = "camera_rigs"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    frame_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    view_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    anchor_asset_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    background_mask_asset_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    preservation_mode: Mapped[str] = mapped_column(String(256), nullable=False)
    camera_device_visibility: Mapped[str] = mapped_column(String(256), nullable=False)
    face_policy: Mapped[str] = mapped_column(String(256), nullable=False)
    qc_profile_id: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(256), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CameraAnchorRow(Base):
    __tablename__ = "camera_anchors"
    __table_args__ = (UniqueConstraint("rig_id", "revision", name="uq_camera_anchor_revision"),)
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    rig_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    image_asset_id: Mapped[str] = mapped_column(String(32), nullable=False)
    bg_mask_asset_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    sha256: Mapped[str] = mapped_column(String(256), nullable=False)
    face_visibility: Mapped[str] = mapped_column(String(256), nullable=False)
    face_check_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ShotCameraBindingRow(Base):
    __tablename__ = "shot_camera_bindings"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    shot_id: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    rig_id: Mapped[str] = mapped_column(String(32), nullable=False)
    rig_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    anchor_asset_sha256: Mapped[str] = mapped_column(String(256), nullable=False)
    face_policy: Mapped[str] = mapped_column(String(256), nullable=False)
    subject_motion: Mapped[str | None] = mapped_column(String(256), nullable=True)
    subject_distance_class: Mapped[str | None] = mapped_column(String(256), nullable=True)
    edit_mask_asset_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    pose_asset_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CameraQCReportRow(Base):
    __tablename__ = "camera_qc_reports"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    attempt_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    candidate_asset_id: Mapped[str] = mapped_column(String(32), nullable=False)
    scores_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    decision: Mapped[str] = mapped_column(String(256), nullable=False)
    reason_codes_json: Mapped[list] = mapped_column(JSON, nullable=False)
    version: Mapped[str] = mapped_column(String(256), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
