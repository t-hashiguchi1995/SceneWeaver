"""Stable Camera Lock errors shared by services and HTTP adapters."""

CAMERA_RIG_STALE = "CAMERA_RIG_STALE"
ANCHOR_FACE_INVALID = "ANCHOR_FACE_INVALID"
CAMERA_LOCK_CAPABILITY_UNAVAILABLE = "CAMERA_LOCK_CAPABILITY_UNAVAILABLE"
REFERENCE_ASSET_INVALID = "REFERENCE_ASSET_INVALID"
MASK_OUT_OF_BOUNDS = "MASK_OUT_OF_BOUNDS"
PROJECT_SCOPE_MISMATCH = "PROJECT_SCOPE_MISMATCH"
CAMERA_RIG_NOT_FOUND = "CAMERA_RIG_NOT_FOUND"
CAMERA_LOCK_NOT_BOUND = "CAMERA_LOCK_NOT_BOUND"


class CameraLockError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def http_status_for_camera_code(code: str) -> int:
    return {
        CAMERA_RIG_STALE: 409,
        PROJECT_SCOPE_MISMATCH: 403,
        CAMERA_RIG_NOT_FOUND: 404,
        CAMERA_LOCK_NOT_BOUND: 400,
    }.get(code, 422)
