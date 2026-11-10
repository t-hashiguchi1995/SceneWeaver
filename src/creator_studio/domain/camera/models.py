from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime

from creator_studio.domain.ids import ProjectId, ShotId
from creator_studio.domain.timeutil import utc_now


@dataclass
class CameraRig:
    id: str
    project_id: ProjectId
    name: str
    frame: dict
    revision: int = 1
    view: dict = field(
        default_factory=lambda: {
            "mode": "reference_2d",
            "azimuth_deg": 0,
            "elevation_deg": 12,
            "roll_deg": 0,
            "geometry_verified": False,
        }
    )
    anchor_asset_id: str | None = None
    background_mask_asset_id: str | None = None
    preservation_mode: str = "strict"
    camera_device_visibility: str = "forbidden"
    face_policy: str = "full_visible"
    qc_profile_id: str = "livestream_v1"
    status: str = "draft"
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> dict:
        result = asdict(self)
        for key in ("created_at", "updated_at"):
            if key in result:
                result[key] = result[key].isoformat()
        return result


@dataclass
class CameraAnchor:
    id: str
    rig_id: str
    revision: int
    image_asset_id: str
    bg_mask_asset_id: str | None
    sha256: str
    face_visibility: str
    face_check: dict
    created_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> dict:
        result = asdict(self)
        for key in ("created_at", "updated_at"):
            if key in result:
                result[key] = result[key].isoformat()
        return result


@dataclass
class ShotCameraBinding:
    id: str
    shot_id: ShotId
    rig_id: str
    rig_revision: int
    anchor_asset_sha256: str
    face_policy: str
    subject_motion: str | None
    subject_distance_class: str | None
    edit_mask_asset_id: str | None
    pose_asset_id: str | None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> dict:
        result = asdict(self)
        for key in ("created_at", "updated_at"):
            if key in result:
                result[key] = result[key].isoformat()
        return result


@dataclass
class CameraQCReport:
    id: str
    attempt_id: str
    candidate_asset_id: str
    scores: dict
    decision: str
    reason_codes: list[str]
    version: str
    created_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> dict:
        result = asdict(self)
        for key in ("created_at", "updated_at"):
            if key in result:
                result[key] = result[key].isoformat()
        return result
