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


@dataclass
class RawFace:
    bbox: tuple[float, float, float, float]
    landmarks: dict[str, tuple[float, float]]
    score: float


def classify_face_visibility(width, height, faces) -> FaceVisibilityResult:
    if not faces:
        return FaceVisibilityResult("not_found", {"checker": "yunet", "faces": 0})
    face = max(faces, key=lambda face: face.score)
    names = ("right_eye", "left_eye", "nose", "right_mouth", "left_mouth")
    landmarks = {
        name: {
            "x": face.landmarks[name][0],
            "y": face.landmarks[name][1],
            "inside": 0 <= face.landmarks[name][0] < width
            and 0 <= face.landmarks[name][1] < height,
        }
        for name in names
    }
    missing = [name for name, point in landmarks.items() if not point["inside"]]
    x, y, w, h = face.bbox
    margin = y / height
    crosses = x < 0 or y < 0 or x + w > width or y + h > height
    status = (
        "cropped"
        if crosses or (not missing and margin < 0.03)
        else ("partial" if missing else "full_visible")
    )
    return FaceVisibilityResult(
        status,
        {
            "checker": "yunet",
            "faces": len(faces),
            "bbox": face.bbox,
            "score": face.score,
            "head_top_margin": margin,
            "landmarks": landmarks,
            "landmarks_missing": missing,
        },
    )


class YuNetFaceVisibilityChecker:
    def __init__(self):
        self._detector = None

    def _detect_raw(self, image_bytes) -> list[RawFace]:
        import io
        from pathlib import Path

        import cv2
        import numpy as np
        from PIL import Image

        if self._detector is None:
            model = (
                Path(__file__).resolve().parents[4]
                / "assets"
                / "models"
                / "face_detection_yunet_2023mar.onnx"
            )
            self._detector = cv2.FaceDetectorYN.create(str(model), "", (320, 320), 0.6, 0.3, 5000)
        with Image.open(io.BytesIO(image_bytes)) as image:
            rgb = np.array(image.convert("RGB"))
            self._detector.setInputSize(image.size)
        _, rows = self._detector.detect(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
        names = ("right_eye", "left_eye", "nose", "right_mouth", "left_mouth")
        return (
            [
                RawFace(
                    tuple(float(v) for v in row[:4]),
                    {
                        name: (float(row[4 + 2 * i]), float(row[5 + 2 * i]))
                        for i, name in enumerate(names)
                    },
                    float(row[14]),
                )
                for row in rows
            ]
            if rows is not None
            else []
        )

    def check(self, image_bytes) -> FaceVisibilityResult:
        try:
            import io

            from PIL import Image

            with Image.open(io.BytesIO(image_bytes)) as image:
                width, height = image.size
            return classify_face_visibility(width, height, self._detect_raw(image_bytes))
        except Exception as exc:  # noqa: BLE001 - unavailable capabilities must remain unknown
            return FaceVisibilityResult(
                "unknown", {"reason": "face_detector_error", "error": str(exc), "checker": "yunet"}
            )
