from dataclasses import dataclass
from typing import Protocol


@dataclass
class FaceVisibilityResult:
    status: str
    detail: dict


class FaceVisibilityChecker(Protocol):
    def check(self, image_bytes: bytes) -> FaceVisibilityResult: ...


class UnavailableFaceVisibilityChecker:
    def check(self, image_bytes: bytes) -> FaceVisibilityResult:
        return FaceVisibilityResult(
            "unknown", {"reason": "no_face_detector_available", "checker": "unavailable"}
        )
