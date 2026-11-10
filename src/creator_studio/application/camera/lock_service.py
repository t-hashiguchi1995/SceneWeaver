from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass
from math import gcd

from PIL import Image

from creator_studio.application.camera.face_visibility import (
    FaceVisibilityChecker,
    UnavailableFaceVisibilityChecker,
)
from creator_studio.domain.camera.errors import (
    ANCHOR_FACE_INVALID,
    CAMERA_LOCK_CAPABILITY_UNAVAILABLE,
    CAMERA_LOCK_NOT_BOUND,
    CAMERA_RIG_NOT_FOUND,
    CAMERA_RIG_STALE,
    PROJECT_SCOPE_MISMATCH,
    REFERENCE_ASSET_INVALID,
    CameraLockError,
)
from creator_studio.domain.camera.models import CameraAnchor, CameraRig, ShotCameraBinding
from creator_studio.domain.ids import new_id
from creator_studio.domain.timeutil import utc_now
from creator_studio.infrastructure.workflows.registry_models import (
    resolve_template_id_for_capability,
)
from creator_studio.ports.asset_store import AssetStore
from creator_studio.ports.unit_of_work import UnitOfWork


@dataclass
class CameraLockRequest:
    enabled: bool = False
    rig_id: str | None = None
    expected_rig_revision: int | None = None
    strategy: str | None = None
    pose_asset_id: str | None = None
    edit_mask_asset_id: str | None = None


class CameraLockService:
    def __init__(
        self, uow: UnitOfWork, store: AssetStore, checker: FaceVisibilityChecker | None = None
    ):
        self._uow = uow
        self._store = store
        self._checker = checker if checker is not None else UnavailableFaceVisibilityChecker()

    @staticmethod
    def _frame(width, height):
        if type(width) is not int or type(height) is not int or width <= 0 or height <= 0:
            raise ValueError("frame dimensions must be positive integers")
        divisor = gcd(width, height)
        return {
            "width": width,
            "height": height,
            "aspect": f"{width // divisor}:{height // divisor}",
        }

    @staticmethod
    def _validate(rig):
        for key, allowed in {
            "preservation_mode": ("strict", "semantic", "off"),
            "camera_device_visibility": ("forbidden", "allowed"),
            "face_policy": ("full_visible", "partial_allowed", "not_required"),
            "status": ("draft", "locked"),
        }.items():
            if getattr(rig, key) not in allowed:
                raise ValueError(f"invalid {key}")
        if not isinstance(rig.name, str) or not isinstance(rig.qc_profile_id, str):
            raise ValueError("name and qc_profile_id must be strings")
        if not isinstance(rig.view, dict) or rig.view.keys() - {
            "mode",
            "azimuth_deg",
            "elevation_deg",
            "roll_deg",
            "geometry_verified",
        }:
            raise ValueError("invalid view fields")
        if rig.view.get("mode") != "reference_2d":
            raise ValueError("invalid view mode")

    @staticmethod
    def _rig(uow, rig_id):
        rig = uow.camera_rigs.get(rig_id)
        if rig is None:
            raise ValueError("camera rig not found")
        return rig

    @staticmethod
    def _project(uow, shot_id):
        shot = uow.shots.get(shot_id)
        if shot is None:
            raise ValueError("shot not found")
        beat = uow.beats.get(shot.beat_id)
        scene = uow.scenes.get(beat.scene_id) if beat else None
        project = uow.projects.get(scene.project_id) if scene else None
        if project is None:
            raise ValueError("shot project not found")
        return str(project.id)

    @staticmethod
    def _binding(uow, shot_id):
        return next(iter(uow.shot_camera_bindings.list_for_shot(shot_id)), None)

    @staticmethod
    def _anchor(uow, rig):
        anchors = [
            a
            for a in uow.camera_anchors.list_for_rig(rig.id)
            if a.image_asset_id == rig.anchor_asset_id
        ]
        return max(anchors, key=lambda a: a.revision, default=None)

    def create_rig(
        self,
        project_id,
        *,
        name,
        frame_width,
        frame_height,
        view=None,
        mode="reference_2d",
        azimuth_deg=0,
        elevation_deg=12,
        roll_deg=0,
        geometry_verified=False,
        preservation_mode="strict",
        camera_device_visibility="forbidden",
        face_policy="full_visible",
        qc_profile_id="livestream_v1",
        background_mask_asset_id=None,
    ):
        with self._uow as uow:
            if uow.projects.get(project_id) is None:
                raise ValueError("project not found")
            rig = CameraRig(
                id=new_id(),
                project_id=project_id,
                name=name,
                frame=self._frame(frame_width, frame_height),
                view={
                    "mode": mode,
                    "azimuth_deg": azimuth_deg,
                    "elevation_deg": elevation_deg,
                    "roll_deg": roll_deg,
                    "geometry_verified": geometry_verified,
                    **(view or {}),
                },
                preservation_mode=preservation_mode,
                camera_device_visibility=camera_device_visibility,
                face_policy=face_policy,
                qc_profile_id=qc_profile_id,
                background_mask_asset_id=background_mask_asset_id,
            )
            self._validate(rig)
            uow.camera_rigs.add(rig)
            uow.commit()
            return rig

    def list_rigs(self, project_id):
        with self._uow as uow:
            return uow.camera_rigs.list_for_project(project_id)

    def get_rig(self, rig_id):
        with self._uow as uow:
            return self._rig(uow, rig_id)

    def update_rig(self, rig_id, *, expected_revision, patch):
        with self._uow as uow:
            rig = self._rig(uow, rig_id)
            if rig.revision != expected_revision:
                raise CameraLockError(CAMERA_RIG_STALE, "camera rig revision is stale")
            allowed = {
                "name",
                "frame",
                "view",
                "preservation_mode",
                "camera_device_visibility",
                "face_policy",
                "qc_profile_id",
                "background_mask_asset_id",
                "status",
            }
            if patch.keys() - allowed:
                raise ValueError("unsupported camera rig patch fields")
            for key, value in patch.items():
                if key in ("frame", "view") and not isinstance(value, dict):
                    raise ValueError(f"{key} must be an object")
                if key == "frame":
                    if value.keys() - {"width", "height"}:
                        raise ValueError("frame accepts width and height only")
                    value = self._frame(
                        value.get("width", rig.frame["width"]),
                        value.get("height", rig.frame["height"]),
                    )
                elif key == "view":
                    value = {**rig.view, **value}
                setattr(rig, key, value)
            self._validate(rig)
            rig.revision += 1
            rig.updated_at = utc_now()
            uow.camera_rigs.save(rig)
            uow.commit()
            return rig

    def register_anchor(self, rig_id, image_asset_id, bg_mask_asset_id=None):
        with self._uow as uow:
            rig = self._rig(uow, rig_id)
            asset = uow.assets.get(image_asset_id)
            if asset is None:
                raise CameraLockError(REFERENCE_ASSET_INVALID, "anchor asset not found")
            try:
                data = self._store.path_for_uri(asset.uri).read_bytes()
                sha = hashlib.sha256(data).hexdigest()
                if sha != asset.sha256 or len(data) != asset.byte_size:
                    raise ValueError("anchor asset integrity mismatch")
                with Image.open(io.BytesIO(data)) as image:
                    image.load()
                    ratio = rig.frame["width"] / rig.frame["height"]
                    if abs(image.width / image.height - ratio) / ratio > 0.01:
                        raise ValueError("anchor aspect does not match rig frame")
            except (OSError, ValueError, Image.DecompressionBombError) as exc:
                raise CameraLockError(REFERENCE_ASSET_INVALID, str(exc)) from exc
            result = self._checker.check(data)
            if rig.face_policy == "full_visible" and result.status != "full_visible":
                reason = (
                    "face_visibility_unverified"
                    if result.status == "unknown"
                    else "anchor face is not fully visible"
                )
                raise CameraLockError(ANCHOR_FACE_INVALID, reason)
            if rig.face_policy == "partial_allowed" and result.status == "cropped":
                raise CameraLockError(ANCHOR_FACE_INVALID, "anchor face is cropped")
            revision = (
                max((a.revision for a in uow.camera_anchors.list_for_rig(rig_id)), default=0) + 1
            )
            anchor = CameraAnchor(
                new_id(),
                rig_id,
                revision,
                image_asset_id,
                bg_mask_asset_id,
                sha,
                result.status,
                result.detail,
            )
            uow.camera_anchors.add(anchor)
            rig.anchor_asset_id = image_asset_id
            rig.updated_at = utc_now()
            uow.camera_rigs.save(rig)
            uow.commit()
            return anchor

    def bind_shot(
        self,
        shot_id,
        rig_id,
        *,
        face_policy,
        subject_motion=None,
        subject_distance_class=None,
        edit_mask_asset_id=None,
        pose_asset_id=None,
    ):
        with self._uow as uow:
            project_id = self._project(uow, shot_id)
            rig = self._rig(uow, rig_id)
            if project_id != rig.project_id:
                raise CameraLockError(
                    PROJECT_SCOPE_MISMATCH, "shot and rig belong to different projects"
                )
            if face_policy not in ("full_visible", "partial_allowed"):
                raise ValueError("invalid binding face_policy")
            anchor = self._anchor(uow, rig)
            if not rig.anchor_asset_id or anchor is None:
                raise CameraLockError(REFERENCE_ASSET_INVALID, "rig has no canonical anchor")
            for asset_id in (edit_mask_asset_id, pose_asset_id):
                if asset_id and uow.assets.get(asset_id) is None:
                    raise CameraLockError(REFERENCE_ASSET_INVALID, "binding asset not found")
            old = self._binding(uow, shot_id)
            binding = ShotCameraBinding(
                old.id if old else new_id(),
                shot_id,
                rig_id,
                rig.revision,
                anchor.sha256,
                face_policy,
                subject_motion,
                subject_distance_class,
                edit_mask_asset_id,
                pose_asset_id,
            )
            if old:
                binding.created_at = old.created_at
            uow.shot_camera_bindings.save(binding)
            uow.commit()
            return binding

    def get_binding(self, shot_id):
        with self._uow as uow:
            return self._binding(uow, shot_id)

    def current_anchor(self, rig_id):
        with self._uow as uow:
            return self._anchor(uow, self._rig(uow, rig_id))

    def camera_provenance(self, shot_id, *, uow=None):
        if uow is None:
            with self._uow as opened:
                return self.camera_provenance(shot_id, uow=opened)
        binding = self._binding(uow, shot_id)
        if binding is None:
            return None
        rig = self._rig(uow, binding.rig_id)
        mask = uow.assets.get(binding.edit_mask_asset_id) if binding.edit_mask_asset_id else None
        return {
            "camera_rig_id": binding.rig_id,
            "camera_rig_revision": binding.rig_revision,
            "anchor_sha256": binding.anchor_asset_sha256,
            "mask_sha256": mask.sha256 if mask else None,
            "camera_lock_workflow_hash": None,
            "qc_profile_version": rig.qc_profile_id,
        }

    def attempt_camera_staleness(self, attempt):
        payload = attempt.payload
        if "camera_rig_id" not in payload:
            return None
        with self._uow as uow:
            rig = uow.camera_rigs.get(payload["camera_rig_id"])
            if rig is None or rig.revision != payload.get("camera_rig_revision"):
                return True
            anchor = self._anchor(uow, rig)
            return anchor is not None and anchor.sha256 != payload.get("anchor_sha256")

    def validate_render_request(self, shot_id, req, *, uow=None):
        if uow is None:
            with self._uow as opened:
                return self.validate_render_request(shot_id, req, uow=opened)
        binding = self._binding(uow, shot_id)
        rig_id = req.rig_id or (binding.rig_id if binding else None)
        if rig_id is None:
            raise CameraLockError(CAMERA_LOCK_NOT_BOUND, "camera lock has no rig binding")
        rig = uow.camera_rigs.get(rig_id)
        if rig is None:
            raise CameraLockError(CAMERA_RIG_NOT_FOUND, "camera rig not found")
        if binding and req.rig_id and req.rig_id != binding.rig_id:
            raise CameraLockError(
                PROJECT_SCOPE_MISMATCH, "rig_id does not match the shot's camera binding"
            )
        if rig.project_id != self._project(uow, shot_id):
            raise CameraLockError(
                PROJECT_SCOPE_MISMATCH, "shot and rig belong to different projects"
            )
        expected = (
            req.expected_rig_revision
            if req.expected_rig_revision is not None
            else (binding.rig_revision if binding else rig.revision)
        )
        if expected != rig.revision:
            raise CameraLockError(CAMERA_RIG_STALE, "camera rig revision is stale")
        try:
            resolve_template_id_for_capability("CameraLockedRender")
        except ValueError as exc:
            raise CameraLockError(
                CAMERA_LOCK_CAPABILITY_UNAVAILABLE,
                "CameraLockedRender workflow is not available for any approved model",
            ) from exc
