from __future__ import annotations

import io
import random

import httpx
import pytest
from PIL import Image, ImageDraw
from sqlalchemy import update

from creator_studio.application.camera import device_checker as devices
from creator_studio.application.camera.face_visibility import (
    FaceVisibilityResult,
    RawFace,
    YuNetFaceVisibilityChecker,
    classify_face_visibility,
)
from creator_studio.application.camera.lock_service import CameraLockRequest, CameraLockService
from creator_studio.application.camera.qc import (
    CameraQCService,
    _landmark_drift,
    protected_background,
)
from creator_studio.domain.camera.errors import CameraLockError
from creator_studio.infrastructure.db.models import GenerationAttemptRow
from tests.unit.test_camera_api import client_for
from tests.unit.test_camera_lock_p1 import bound, png_bytes, project, store_png


class Face:
    def __init__(self, status="full_visible", detail=None):
        self.status, self.detail = status, detail or {}

    def check(self, data):
        return FaceVisibilityResult(self.status, self.detail)


class Device:
    def __init__(self, outcome="clear"):
        self.outcome = outcome

    def check(self, data):
        return self.outcome, {}


def raw(bbox=(10, 10, 60, 60), outside=False):
    points = {
        name: (30.0, 40.0)
        for name in ("right_eye", "left_eye", "nose", "right_mouth", "left_mouth")
    }
    if outside:
        points["nose"] = (-1.0, 40.0)
    return RawFace(bbox, points, 0.95)


@pytest.mark.parametrize(
    "faces,status",
    [
        ([raw()], "full_visible"),
        ([raw((-1, 10, 60, 60))], "cropped"),
        ([raw((10, 2, 60, 60))], "cropped"),
        ([raw(outside=True)], "partial"),
        ([], "not_found"),
    ],
)
def test_classify(faces, status):
    assert classify_face_visibility(100, 100, faces).status == status


def test_real_detector_and_raw_boundary(monkeypatch):
    checker = YuNetFaceVisibilityChecker()
    data = png_bytes((100, 100), "white")
    assert checker.check(data).status == "not_found"
    monkeypatch.setattr(checker, "_detect_raw", lambda _: [raw()])
    assert checker.check(data).status == "full_visible"
    assert checker.check(b"bad").status == "unknown"


def texture():
    rng = random.Random(21)
    image = Image.new("RGB", (1536, 864), "white")
    draw = ImageDraw.Draw(image)
    for _ in range(3500):
        x, y = rng.randrange(1530), rng.randrange(858)
        draw.rectangle((x, y, x + 5, y + 5), fill=tuple(rng.randrange(256) for _ in range(3)))
    return image


def encode(image):
    out = io.BytesIO()
    image.save(out, format="PNG")
    return out.getvalue()


@pytest.mark.parametrize("shift,status", [(0, "pass"), (10, "review")])
def test_landmark_texture(shift, status):
    anchor = texture()
    candidate = Image.new("RGB", anchor.size, "white")
    candidate.paste(anchor, (shift, 0))
    result = _landmark_drift(encode(anchor), encode(candidate), png_bytes(anchor.size, "black"))
    assert result["status"] == status
    if shift:
        assert result["median_px"] > 6
        assert result["reason"] == "LANDMARK_DRIFT_ABOVE_TARGET"


def test_blank_landmarks():
    data = png_bytes((100, 100), "white")
    result = _landmark_drift(data, data, png_bytes((100, 100), "black"))
    assert result["status"] == "review"
    assert result["reason"] == "LANDMARK_MATCH_INSUFFICIENT"


@pytest.mark.parametrize("inside", [True, False])
def test_background(inside):
    data = png_bytes((100, 100), "black")
    candidate = png_bytes(
        (100, 100), "black", rectangle=(40, 40, 50, 50) if inside else (0, 0, 15, 15)
    )
    result = protected_background(
        data, candidate, png_bytes((100, 100), "black", rectangle=(30, 30, 60, 60))
    )
    assert result["status"] == ("pass" if inside else "fail")
    if not inside:
        assert result["reason"] == "PROTECTED_BACKGROUND_CHANGED"


@pytest.mark.parametrize(
    "policy,face,status,reason",
    [
        ("full_visible", Face("cropped"), "fail", "FACE_NOT_FULLY_VISIBLE"),
        (
            "partial_allowed",
            Face("partial", {"landmarks": {"left_mouth": {"inside": True}}}),
            "pass",
            None,
        ),
        ("partial_allowed", Face("not_found"), "fail", "FACE_NOT_VISIBLE"),
        ("full_visible", Face("unknown"), "unknown", None),
    ],
)
def test_face_policy(policy, face, status, reason):
    result = CameraQCService(None, None, face, Device()).face_visibility(b"", policy)
    assert result["status"] == status
    assert result.get("reason") == reason


def attempt(container):
    s, pipeline, _, _ = bound(container)
    result = pipeline.render(s.id, camera_lock=CameraLockRequest(enabled=True))
    assert len(result["camera_qc"]) == len(result["output_asset_ids"])
    return s, pipeline, result


def test_frame_mismatch_and_persistence(container):
    _s, _pipeline, result = attempt(container)
    aid = result["generation_attempt_id"]
    wrong = store_png(container, png_bytes((100, 100), "white"))
    with container.uow() as uow:
        a = uow.generation_attempts.get(aid)
        a.output_asset_ids = [wrong.id]
        uow.session.execute(
            update(GenerationAttemptRow)
            .where(GenerationAttemptRow.id == a.id)
            .values(output_asset_ids_json=a.output_asset_ids, payload_json=a.payload)
        )
        uow.commit()
    service = CameraQCService(container.uow(), container.asset_store, Face(), Device())
    reports = service.run_for_attempt(aid)
    assert reports[0].decision == "fail"
    assert "FRAME_SIZE_MISMATCH" in reports[0].reason_codes
    assert service.list_reports(aid)


def test_unknown_caps_at_review(container, monkeypatch):
    _s, _pipeline, result = attempt(container)
    monkeypatch.setattr(
        "creator_studio.application.camera.qc._landmark_drift", lambda *a: {"status": "pass"}
    )
    service = CameraQCService(container.uow(), container.asset_store, Face(), Device("unavailable"))
    report = service.run_for_attempt(result["generation_attempt_id"])[0]
    assert report.decision == "review"
    assert report.reason_codes == ["VLM_UNAVAILABLE"]


def test_api(container):
    s, pipeline, result = attempt(container)
    client = client_for(container)
    url = f"/api/v1/generations/{result['generation_attempt_id']}/camera-qc"
    response = client.post(url)
    assert response.status_code == 200
    saved = client.get(url).json()["items"]
    assert all(r in saved for r in response.json()["items"])
    assert client.get(url, params={"candidate_asset_id": "missing"}).status_code == 404
    assert client.get("/api/v1/generations/missing/camera-qc").status_code == 404
    assert client.post("/api/v1/generations/missing/camera-qc").status_code == 404
    plain = pipeline.render(s.id)
    assert (
        client.post(f"/api/v1/generations/{plain['generation_attempt_id']}/camera-qc").status_code
        == 200
    )
    # A binding can attach provenance to a plain render; explicitly remove it.
    with container.uow() as uow:
        a = uow.generation_attempts.get(plain["generation_attempt_id"])
        a.payload = {k: v for k, v in a.payload.items() if k != "camera_rig_id"}
        uow.session.execute(
            update(GenerationAttemptRow)
            .where(GenerationAttemptRow.id == a.id)
            .values(output_asset_ids_json=a.output_asset_ids, payload_json=a.payload)
        )
        uow.commit()
    assert (
        client.post(f"/api/v1/generations/{plain['generation_attempt_id']}/camera-qc").status_code
        == 400
    )


def test_real_anchor_gate(container):
    p = project(container)
    service = CameraLockService(container.uow(), container.asset_store)
    asset = store_png(container, png_bytes((100, 100), "white"))
    for policy in ("full_visible", "partial_allowed"):
        rig = service.create_rig(
            p.id, name=policy, frame_width=100, frame_height=100, face_policy=policy
        )
        if policy == "full_visible":
            with pytest.raises(CameraLockError) as exc:
                service.register_anchor(rig.id, asset.id)
            assert exc.value.code == "ANCHOR_FACE_INVALID"
        else:
            assert service.register_anchor(rig.id, asset.id).face_visibility == "not_found"


@pytest.mark.parametrize(
    "flags,confidence,outcome",
    [(False, 0.9, "clear"), (True, 0.9, "violation"), (True, 0.5, "suspected")],
)
def test_vlm_vision(monkeypatch, flags, confidence, outcome):
    import json

    calls = []

    def handler(request):
        calls.append(request)
        if request.method == "GET":
            return httpx.Response(
                200, json={"models": [{"name": "vision", "capabilities": ["vision"]}]}
            )
        return httpx.Response(
            200,
            json={
                "message": {
                    "content": json.dumps(
                        {
                            "camera_device_visible": flags,
                            "lcd_frame_visible": False,
                            "monitor_in_frame_view": False,
                            "confidence": confidence,
                        }
                    )
                }
            },
        )

    original = httpx.Client
    monkeypatch.setattr(
        devices.httpx, "Client", lambda **kw: original(transport=httpx.MockTransport(handler), **kw)
    )
    assert devices.OllamaCameraDeviceChecker(model="vision").check(b"png")[0] == outcome
    assert len(calls) == 2


def test_vlm_negative_cache(monkeypatch):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(
            200, json={"models": [{"name": "no-vision", "capabilities": ["completion"]}]}
        )

    original = httpx.Client
    monkeypatch.setattr(
        devices.httpx, "Client", lambda **kw: original(transport=httpx.MockTransport(handler), **kw)
    )
    checker = devices.OllamaCameraDeviceChecker(model="no-vision")
    devices._NEGATIVE_AVAILABILITY.clear()
    assert checker.check(b"png")[0] == "unavailable"
    assert checker.check(b"png")[0] == "unavailable"
    assert len(calls) == 1


@pytest.mark.parametrize(
    "missing,reason", [("anchor", "ANCHOR_MISSING"), ("mask", "EDIT_MASK_MISSING")]
)
def test_missing_dependencies(container, missing, reason):
    s, _pipeline, result = attempt(container)
    with container.uow() as uow:
        binding = uow.shot_camera_bindings.list_for_shot(s.id)[0]
        if missing == "anchor":
            rig = uow.camera_rigs.get(binding.rig_id)
            rig.anchor_asset_id = None
            uow.camera_rigs.save(rig)
        else:
            binding.edit_mask_asset_id = None
            uow.shot_camera_bindings.save(binding)
        uow.commit()
    service = CameraQCService(container.uow(), container.asset_store, Face(), Device())
    report = service.run_for_attempt(result["generation_attempt_id"])[0]
    assert report.decision == "review"
    for name in ("protected_background", "static_landmark_drift"):
        assert report.scores["checks"][name]["status"] == "unknown"
        assert report.scores["checks"][name]["reason"] == reason
    assert report.scores["checks"]["frame_ratio"]["status"] == "pass"
    assert report.scores["checks"]["face_visibility"]["status"] == "pass"


def test_pipeline_qc_exception_preserves_attempt(container):
    s, pipeline, _, _ = bound(container)

    class BrokenQC:
        def run_for_attempt(self, _):
            raise RuntimeError("QC unavailable")

    pipeline._camera_qc = BrokenQC()
    result = pipeline.render(s.id, camera_lock=CameraLockRequest(enabled=True))
    assert result["camera_qc_error"] == "QC unavailable"
    assert pipeline.get_attempt(result["generation_attempt_id"]).output_asset_ids


@pytest.mark.parametrize("response", ["invalid", "missing-fields", "http400"])
def test_vlm_unavailable_responses(monkeypatch, response):
    def handler(request):
        if request.method == "GET":
            return httpx.Response(200, json={"models": [{"name": "future"}]})
        if response == "http400":
            return httpx.Response(400, text="model does not support multimodal requests")
        return httpx.Response(
            200, json={"message": {"content": "oops" if response == "invalid" else "{}"}}
        )

    original = httpx.Client
    monkeypatch.setattr(
        devices.httpx, "Client", lambda **kw: original(transport=httpx.MockTransport(handler), **kw)
    )
    outcome, detail = devices.OllamaCameraDeviceChecker(model="future").check(b"png")
    assert outcome == "unavailable"
    assert detail["reason"] == (
        "VLM_UNAVAILABLE" if response == "http400" else "VLM_RESPONSE_INVALID"
    )
