import io
from pathlib import Path

import pytest
from PIL import Image

from creator_studio.application.camera.face_visibility import (
    YoloFace,
    YoloFaceVisibilityChecker,
    classify_face_visibility_yolo,
)
from tests.unit.test_camera_lock_p1 import png_bytes

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


@pytest.mark.parametrize(
    "faces,status",
    [
        ([YoloFace((10, 10, 60, 60), 0.9)], "full_visible"),
        ([YoloFace((10, 2, 60, 60), 0.9)], "cropped"),
        ([YoloFace((10, -20, 60, 60), 0.9)], "cropped"),
        ([YoloFace((-10, 10, 60, 60), 0.9)], "partial"),
        ([YoloFace((10, 50, 60, 60), 0.9)], "partial"),
        ([YoloFace((90, 10, 60, 60), 0.9)], "cropped"),
        ([], "not_found"),
    ],
)
def test_classify(faces, status):
    result = classify_face_visibility_yolo(100, 100, faces)
    assert result.status == status
    if status == "full_visible":
        assert result.detail["method"] == "yolo_bbox"
        assert "landmarks" not in result.detail
        assert result.detail["head_top_margin"] == pytest.approx(0.10)


def test_raw_boundary(monkeypatch):
    checker = YoloFaceVisibilityChecker()
    monkeypatch.setattr(
        checker, "_detect_raw", lambda _: [YoloFace((10, 10, 60, 60), 0.9)]
    )
    assert checker.check(png_bytes((100, 100), "white")).status == "full_visible"
    assert checker.check(b"bad").status == "unknown"


def test_real_detector_canonical_fullbody():
    result = YoloFaceVisibilityChecker().check(
        (FIXTURES / "characters/char_a/canonical_fullbody.png").read_bytes()
    )
    assert result.status == "full_visible"
    assert result.detail["method"] == "yolo_bbox"
    assert result.detail["score"] >= 0.5
    assert result.detail["head_top_margin"] >= 0.03


def test_real_detector_cardigan():
    result = YoloFaceVisibilityChecker().check(
        (FIXTURES / "garments/cardigan_plate.png").read_bytes()
    )
    assert result.status == "full_visible"


def test_real_detector_blank():
    assert (
        YoloFaceVisibilityChecker().check(png_bytes((100, 100), "white")).status == "not_found"
    )


def test_real_detector_cropped():
    with Image.open(FIXTURES / "characters/char_a/canonical_fullbody.png") as image:
        cropped = image.crop((0, 150, image.width, image.height))
        out = io.BytesIO()
        cropped.save(out, format="PNG")
    assert YoloFaceVisibilityChecker().check(out.getvalue()).status != "full_visible"
