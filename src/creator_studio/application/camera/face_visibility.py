from dataclasses import dataclass
from typing import Protocol

from .qc_profile import (
    FACE_HEAD_TOP_MARGIN_MIN,
    FACE_YOLO_CONFIDENCE_MIN,
    FACE_YOLO_NMS_IOU_MAX,
)


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
        if crosses or (not missing and margin < FACE_HEAD_TOP_MARGIN_MIN)
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


@dataclass
class YoloFace:
    bbox: tuple[float, float, float, float]
    score: float


def classify_face_visibility_yolo(width, height, faces) -> FaceVisibilityResult:
    if not faces:
        return FaceVisibilityResult(
            "not_found", {"checker": "yolo", "method": "yolo_bbox", "faces": 0}
        )
    face = max(faces, key=lambda face: face.score)
    x, y, w, h = face.bbox
    margin = y / height
    cx, cy = x + w / 2, y + h / 2
    center_inside = 0 <= cx < width and 0 <= cy < height
    tol = 1.0
    fully_inside = x >= -tol and y >= -tol and x + w <= width + tol and y + h <= height + tol
    if margin < FACE_HEAD_TOP_MARGIN_MIN:
        status = "cropped"
    elif fully_inside:
        status = "full_visible"
    elif center_inside:
        status = "partial"
    else:
        status = "cropped"
    return FaceVisibilityResult(
        status,
        {
            "checker": "yolo",
            "method": "yolo_bbox",
            "faces": len(faces),
            "bbox": face.bbox,
            "score": face.score,
            "confidence": face.score,
            "head_top_margin": margin,
            "margins": {
                "top": margin,
                "left": x / width,
                "right": (width - (x + w)) / width,
                "bottom": (height - (y + h)) / height,
            },
            "center_inside": center_inside,
            "fully_inside": fully_inside,
        },
    )


class YoloFaceVisibilityChecker:
    _session = None

    def _detect_raw(self, image_bytes) -> list[YoloFace]:
        import io
        from pathlib import Path

        import cv2
        import numpy as np
        import onnxruntime
        from PIL import Image

        if YoloFaceVisibilityChecker._session is None:
            model = (
                Path(__file__).resolve().parents[4]
                / "assets"
                / "models"
                / "face_yolov8m.onnx"
            )
            YoloFaceVisibilityChecker._session = onnxruntime.InferenceSession(str(model))
        session = YoloFaceVisibilityChecker._session
        with Image.open(io.BytesIO(image_bytes)) as image:
            rgb = np.array(image.convert("RGB"))
        height, width = rgb.shape[:2]
        scale = min(640 / width, 640 / height)
        resized_width, resized_height = round(width * scale), round(height * scale)
        pad_x, pad_y = (640 - resized_width) // 2, (640 - resized_height) // 2
        canvas = np.full((640, 640, 3), 114, dtype=np.uint8)
        canvas[pad_y : pad_y + resized_height, pad_x : pad_x + resized_width] = cv2.resize(
            rgb, (resized_width, resized_height)
        )
        input_info = session.get_inputs()[0]
        dtype = np.float16 if input_info.type == "tensor(float16)" else np.float32
        blob = (canvas.transpose(2, 0, 1).astype(np.float32) / 255.0).astype(dtype)[None]
        rows = session.run(None, {input_info.name: blob})[0][0].T
        rows = rows[rows[:, 4] >= FACE_YOLO_CONFIDENCE_MIN]
        boxes, scores = [], []
        for cx, cy, w, h, score in rows:
            boxes.append([float(cx - w / 2), float(cy - h / 2), float(w), float(h)])
            scores.append(float(score))
        indices = cv2.dnn.NMSBoxes(
            boxes,
            scores,
            score_threshold=FACE_YOLO_CONFIDENCE_MIN,
            nms_threshold=FACE_YOLO_NMS_IOU_MAX,
        )
        faces = []
        for index in np.asarray(indices).reshape(-1):
            x, y, w, h = boxes[index]
            faces.append(
                YoloFace(
                    ((x - pad_x) / scale, (y - pad_y) / scale, w / scale, h / scale),
                    scores[index],
                )
            )
        return faces

    def check(self, image_bytes) -> FaceVisibilityResult:
        try:
            import io

            from PIL import Image

            with Image.open(io.BytesIO(image_bytes)) as image:
                width, height = image.size
            return classify_face_visibility_yolo(width, height, self._detect_raw(image_bytes))
        except Exception as exc:  # noqa: BLE001 - unavailable capabilities must remain unknown
            return FaceVisibilityResult(
                "unknown",
                {
                    "reason": "face_detector_error",
                    "error": str(exc),
                    "checker": "yolo",
                    "method": "yolo_bbox",
                },
            )
