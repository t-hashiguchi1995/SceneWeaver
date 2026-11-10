from __future__ import annotations

import io

from PIL import Image

from creator_studio.domain.camera.models import CameraQCReport
from creator_studio.domain.ids import new_id

from . import composition
from .device_checker import CameraDeviceChecker, OllamaCameraDeviceChecker
from .face_visibility import YuNetFaceVisibilityChecker
from .qc_profile import (
    ANCHOR_MISSING,
    CAMERA_DEVICE_IN_FRAME,
    CAMERA_DEVICE_SUSPECTED,
    EDIT_MASK_MISSING,
    FACE_NOT_FULLY_VISIBLE,
    FACE_NOT_VISIBLE,
    FRAME_SIZE_MISMATCH,
    LANDMARK_DRIFT_ABOVE_TARGET,
    LANDMARK_LOWE_RATIO,
    LANDMARK_MATCH_INSUFFICIENT,
    LANDMARK_MIN_MATCHES,
    LANDMARK_PASS_MAX_PX,
    LANDMARK_REVIEW_MAX_PX,
    PROTECTED_BACKGROUND_CHANGED,
    PROTECTED_CHANGE_MAX_RATIO,
    QC_PROFILE_VERSION,
    VLM_UNAVAILABLE,
)


def _check(status, reason=None, **detail):
    return {**detail, "status": status, **({"reason": reason} if reason else {})}


def frame_ratio(candidate_bytes, rig):
    with Image.open(io.BytesIO(candidate_bytes)) as image:
        width, height = image.size
    return _check(
        "pass" if (width, height) == (rig.frame["width"], rig.frame["height"]) else "fail",
        None
        if (width, height) == (rig.frame["width"], rig.frame["height"])
        else FRAME_SIZE_MISMATCH,
        width=width,
        height=height,
    )


def protected_background(anchor, candidate, mask):
    try:
        ratio = composition.measure_protected_change(anchor, candidate, mask)
        return _check(
            "fail" if ratio > PROTECTED_CHANGE_MAX_RATIO else "pass",
            PROTECTED_BACKGROUND_CHANGED if ratio > PROTECTED_CHANGE_MAX_RATIO else None,
            changed_pixel_ratio=ratio,
        )
    except ValueError as exc:
        return _check(
            "fail", PROTECTED_BACKGROUND_CHANGED, changed_pixel_ratio=None, error=str(exc)
        )


def _landmark_drift(anchor_bytes, candidate_bytes, mask_bytes):
    try:
        import cv2
        import numpy as np

        anchor = np.asarray(composition._open(anchor_bytes, "L"))
        candidate = np.asarray(composition._open(candidate_bytes, "L"))
        mask = np.where(
            np.asarray(composition._dilate(composition._mask(mask_bytes), 8)) == 0, 255, 0
        ).astype("uint8")
        if anchor.shape != candidate.shape or anchor.shape != mask.shape:
            raise ValueError("image size mismatch")
        orb = cv2.ORB_create(nfeatures=2000)
        ka, da = orb.detectAndCompute(anchor, mask)
        kb, db = orb.detectAndCompute(candidate, mask)
        matches = (
            []
            if da is None or db is None
            else [
                pair[0]
                for pair in cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(da, db, k=2)
                if len(pair) == 2 and pair[0].distance < LANDMARK_LOWE_RATIO * pair[1].distance
            ]
        )
        if len(matches) < LANDMARK_MIN_MATCHES:
            return _check("review", LANDMARK_MATCH_INSUFFICIENT, matches=len(matches))
        a = np.float32([ka[m.queryIdx].pt for m in matches])
        b = np.float32([kb[m.trainIdx].pt for m in matches])
        _, inliers = cv2.findHomography(a, b, cv2.RANSAC, 3.0)
        displacement = np.linalg.norm(b - a, axis=1)
        if inliers is not None and np.any(inliers):
            displacement = displacement[inliers.ravel().astype(bool)]
        median = float(np.median(displacement))
        scale = anchor.shape[1] / 1536
        reason = (
            None
            if median <= LANDMARK_PASS_MAX_PX * scale
            else (
                LANDMARK_DRIFT_ABOVE_TARGET
                if median <= LANDMARK_REVIEW_MAX_PX * scale
                else LANDMARK_MATCH_INSUFFICIENT
            )
        )
        return _check(
            "pass" if reason is None else "review", reason, median_px=median, matches=len(matches)
        )
    except Exception as exc:  # noqa: BLE001 - unavailable capabilities must remain unknown
        return _check("unknown", "landmark_error", error=str(exc))


class CameraQCService:
    def __init__(
        self, uow, store, face_checker=None, device_checker: CameraDeviceChecker | None = None
    ):
        self._uow, self._store = uow, store
        self._face = face_checker if face_checker is not None else YuNetFaceVisibilityChecker()
        self._device = device_checker if device_checker is not None else OllamaCameraDeviceChecker()

    def face_visibility(self, candidate, policy):
        result = self._face.check(candidate)
        detail = {"policy": policy, "checker_status": result.status, "detail": result.detail}
        if result.status == "unknown":
            return _check("unknown", result.detail.get("reason"), **detail)
        if policy == "full_visible":
            return _check(
                "pass" if result.status == "full_visible" else "fail",
                None if result.status == "full_visible" else FACE_NOT_FULLY_VISIBLE,
                **detail,
            )
        landmarks = result.detail.get("landmarks")
        if isinstance(landmarks, dict):
            visible = any(
                landmarks.get(name, {}).get("inside", False)
                for name in ("right_eye", "left_eye", "right_mouth", "left_mouth")
            )
            return _check(
                "pass" if visible else "fail", None if visible else FACE_NOT_VISIBLE, **detail
            )
        visible = result.status in ("full_visible", "partial")
        return _check(
            "pass" if visible else "fail",
            None
            if visible
            else FACE_NOT_FULLY_VISIBLE
            if result.status == "cropped"
            else FACE_NOT_VISIBLE,
            **detail,
        )

    def camera_device_in_frame(self, candidate):
        outcome, detail = self._device.check(candidate)
        status, reason = {
            "clear": ("pass", None),
            "violation": ("fail", CAMERA_DEVICE_IN_FRAME),
            "suspected": ("review", CAMERA_DEVICE_SUSPECTED),
            "unavailable": ("unknown", VLM_UNAVAILABLE),
        }[outcome]
        return _check(status, reason, detail=detail)

    def list_reports(self, attempt_id):
        with self._uow as uow:
            if uow.generation_attempts.get(attempt_id) is None:
                raise ValueError("generation attempt not found")
            return uow.camera_qc_reports.list_for_attempt(attempt_id)

    def run_for_attempt(self, attempt_id):
        with self._uow as uow:
            attempt = uow.generation_attempts.get(attempt_id)
            if attempt is None:
                raise ValueError("generation attempt not found")
            if "camera_rig_id" not in attempt.payload:
                raise ValueError("attempt has no camera lock provenance")
            plan = uow.render_plans.get(attempt.render_plan_id)
            if plan is None:
                raise ValueError("render plan not found")
            binding = next(iter(uow.shot_camera_bindings.list_for_shot(plan.shot_id)), None)
            if binding is None:
                raise ValueError("camera binding not found")
            rig = uow.camera_rigs.get(binding.rig_id)
            if rig is None:
                raise ValueError("camera rig not found")

            def load(asset_id):
                asset = uow.assets.get(asset_id) if asset_id else None
                if asset is None:
                    return None
                try:
                    return self._store.path_for_uri(asset.uri).read_bytes()
                except OSError:
                    return None

            anchor, mask = load(rig.anchor_asset_id), load(binding.edit_mask_asset_id)
            missing = (
                ANCHOR_MISSING if anchor is None else EDIT_MASK_MISSING if mask is None else None
            )
            reports = []
            for asset_id in attempt.output_asset_ids:
                candidate = load(asset_id)
                checks = {
                    "frame_ratio": frame_ratio(candidate, rig),
                    "protected_background": _check("unknown", missing)
                    if missing
                    else protected_background(anchor, candidate, mask),
                    "face_visibility": self.face_visibility(candidate, binding.face_policy),
                    "static_landmark_drift": _check("unknown", missing)
                    if missing
                    else _landmark_drift(anchor, candidate, mask),
                    "camera_device_in_frame": self.camera_device_in_frame(candidate),
                }
                statuses = [c["status"] for c in checks.values()]
                decision = (
                    "fail"
                    if "fail" in statuses
                    else "review"
                    if any(s in ("unknown", "review") for s in statuses)
                    else "pass"
                )
                report = CameraQCReport(
                    new_id(),
                    attempt_id,
                    asset_id,
                    {"checks": checks},
                    decision,
                    [
                        c["reason"]
                        for c in checks.values()
                        if c["status"] != "pass" and c.get("reason")
                    ],
                    QC_PROFILE_VERSION,
                )
                uow.camera_qc_reports.add(report)
                reports.append(report)
            uow.commit()
            return reports
