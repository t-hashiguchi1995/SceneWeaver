import hashlib
import io
import json

import pytest
from PIL import Image

from creator_studio.application.assets.store_asset import StoreBytesCommand
from creator_studio.application.camera.face_visibility import FaceVisibilityResult
from creator_studio.application.camera.lock_service import CameraLockRequest, CameraLockService
from creator_studio.application.projects.create_project import CreateProjectCommand
from creator_studio.domain.asset import AssetKind
from creator_studio.domain.camera.errors import CameraLockError


class Checker:
    def __init__(self, status):
        self.status = status

    def check(self, image_bytes):
        return FaceVisibilityResult(self.status, {"checker": "test"})


def project(container):
    return container.create_project().execute(CreateProjectCommand(title="Camera"))


def shot(container, p):
    character = container.create_character().execute("Aiko")
    scene = container.create_scene().execute(p.id, "Studio")
    beat = container.create_beat().execute(scene.id, intent="greet", speaker_id=character.id)
    dialogue = container.dialogue_pipeline().generate_candidates(
        beat_id=beat.id, character_id=character.id
    )
    container.dialogue_pipeline().lock_script_event(dialogue.candidates[0].id, text="Hello")
    return container.shot_pipeline().plan_shot(beat.id)


def png(container, size=(1536, 864), color="white"):
    stream = io.BytesIO()
    Image.new("RGB", size, color).save(stream, format="PNG")
    return container.store_asset().execute(
        StoreBytesCommand(
            stream.getvalue(), AssetKind.GENERATED, "image/png", "camera", "anchor.png"
        )
    )


def service(container, status="full_visible"):
    return CameraLockService(container.uow(), container.asset_store, Checker(status))


def rig(svc, p, **kwargs):
    return svc.create_rig(p.id, name="Studio", frame_width=1536, frame_height=864, **kwargs)


def bound(container):
    p = project(container)
    s = shot(container, p)
    svc = service(container)
    r = rig(svc, p)
    a = svc.register_anchor(r.id, png(container).id)
    b = svc.bind_shot(s.id, r.id, face_policy="partial_allowed")
    return svc, s, r, a, b


def test_rig_defaults_and_revision(container):
    svc = service(container)
    r = rig(svc, project(container))
    assert r.frame == {"width": 1536, "height": 864, "aspect": "16:9"}
    assert r.view == {
        "mode": "reference_2d",
        "azimuth_deg": 0,
        "elevation_deg": 12,
        "roll_deg": 0,
        "geometry_verified": False,
    }
    assert (r.preservation_mode, r.status, r.revision) == ("strict", "draft", 1)
    changed = svc.update_rig(
        r.id, expected_revision=1, patch={"name": "Updated", "view": {"roll_deg": 2}}
    )
    assert (changed.name, changed.revision, changed.view["elevation_deg"]) == ("Updated", 2, 12)
    with pytest.raises(CameraLockError, match="stale") as error:
        svc.update_rig(r.id, expected_revision=1, patch={})
    assert error.value.code == "CAMERA_RIG_STALE"


def test_anchor_integrity_and_sequence(container):
    svc = service(container)
    r = rig(svc, project(container))
    asset = png(container)
    anchor = svc.register_anchor(r.id, asset.id)
    assert (
        anchor.sha256
        == asset.sha256
        == hashlib.sha256(container.asset_store.path_for_uri(asset.uri).read_bytes()).hexdigest()
    )
    assert svc.get_rig(r.id).anchor_asset_id == asset.id
    assert svc.get_rig(r.id).revision == 1
    assert svc.register_anchor(r.id, asset.id).revision == 2
    assert svc.current_anchor(r.id).revision == 2


def test_anchor_aspect(container):
    svc = service(container)
    r = rig(svc, project(container))
    with pytest.raises(CameraLockError) as error:
        svc.register_anchor(r.id, png(container, (1024, 1024)).id)
    assert error.value.code == "REFERENCE_ASSET_INVALID"


@pytest.mark.parametrize("status", ["cropped", "partial", "full_visible"])
def test_face_gate(container, status):
    svc = service(container, status)
    r = rig(svc, project(container))
    asset = png(container)
    if status == "full_visible":
        assert svc.register_anchor(r.id, asset.id).face_visibility == status
    else:
        with pytest.raises(CameraLockError) as error:
            svc.register_anchor(r.id, asset.id)
        assert error.value.code == "ANCHOR_FACE_INVALID"


def test_unknown_face_gate(container):
    svc = CameraLockService(container.uow(), container.asset_store)
    p = project(container)
    asset = png(container)
    with pytest.raises(CameraLockError, match="unverified") as error:
        svc.register_anchor(rig(svc, p).id, asset.id)
    assert error.value.code == "ANCHOR_FACE_INVALID"
    a = svc.register_anchor(rig(svc, p, face_policy="not_required").id, asset.id)
    assert a.face_visibility == "unknown"
    assert a.face_check["reason"] == "no_face_detector_available"


def test_binding_cross_project(container):
    svc = service(container)
    s = shot(container, project(container))
    r = rig(svc, project(container))
    with pytest.raises(CameraLockError) as error:
        svc.bind_shot(s.id, r.id, face_policy="partial_allowed")
    assert error.value.code == "PROJECT_SCOPE_MISMATCH"


def test_binding_snapshots(container):
    svc, s, r, a, b = bound(container)
    assert (b.rig_revision, b.anchor_asset_sha256) == (r.revision, a.sha256)
    svc.update_rig(r.id, expected_revision=1, patch={"name": "Updated"})
    assert svc.get_binding(s.id).to_dict() == b.to_dict()
    rebound = svc.bind_shot(s.id, r.id, face_policy="full_visible")
    assert rebound.rig_revision == 2
    with container.uow() as uow:
        assert len(uow.shot_camera_bindings.list_for_shot(s.id)) == 1


def test_binding_requires_anchor(container):
    svc = service(container)
    p = project(container)
    s = shot(container, p)
    with pytest.raises(CameraLockError) as error:
        svc.bind_shot(s.id, rig(svc, p).id, face_policy="partial_allowed")
    assert error.value.code == "REFERENCE_ASSET_INVALID"


def test_attempt_provenance_and_staleness(container):
    svc, s, r, a, b = bound(container)
    result = container.shot_pipeline().render(s.id)
    attempt = container.shot_pipeline().get_attempt(result["generation_attempt_id"])
    before = json.dumps(attempt.payload, sort_keys=True)
    assert {key: attempt.payload[key] for key in svc.camera_provenance(s.id)} == {
        "camera_rig_id": r.id,
        "camera_rig_revision": b.rig_revision,
        "anchor_sha256": a.sha256,
        "mask_sha256": None,
        "camera_lock_workflow_hash": None,
        "qc_profile_version": "livestream_v1",
    }
    assert svc.attempt_camera_staleness(attempt) is False
    svc.update_rig(r.id, expected_revision=1, patch={"name": "Updated"})
    assert svc.attempt_camera_staleness(attempt) is True
    assert (
        json.dumps(container.shot_pipeline().get_attempt(attempt.id).payload, sort_keys=True)
        == before
    )
    unbound = shot(container, project(container))
    result = container.shot_pipeline().render(unbound.id)
    attempt = container.shot_pipeline().get_attempt(result["generation_attempt_id"])
    assert "camera_rig_id" not in attempt.payload
    assert svc.attempt_camera_staleness(attempt) is None


def test_render_capability_gate(container):
    _svc, s, r, _, _ = bound(container)
    with container.uow() as uow:
        count = len(uow.generation_attempts.list_for_shot(s.id))
    with pytest.raises(CameraLockError) as error:
        container.shot_pipeline().render(
            s.id, camera_lock=CameraLockRequest(enabled=True, expected_rig_revision=r.revision)
        )
    assert error.value.code == "CAMERA_LOCK_CAPABILITY_UNAVAILABLE"
    with container.uow() as uow:
        assert len(uow.generation_attempts.list_for_shot(s.id)) == count


def test_render_stale_first(container):
    _, s, r, _, _ = bound(container)
    with pytest.raises(CameraLockError) as error:
        container.shot_pipeline().render(
            s.id, camera_lock=CameraLockRequest(enabled=True, expected_rig_revision=r.revision + 99)
        )
    assert error.value.code == "CAMERA_RIG_STALE"


def test_render_cross_project(container):
    svc, s, _, _, _ = bound(container)
    other = rig(svc, project(container))
    with pytest.raises(CameraLockError) as error:
        container.shot_pipeline().render(
            s.id, camera_lock=CameraLockRequest(enabled=True, rig_id=other.id)
        )
    assert error.value.code == "PROJECT_SCOPE_MISMATCH"


def test_anchor_rejects_corrupt_stored_bytes(container):
    svc = service(container)
    r = rig(svc, project(container))
    asset = png(container)
    path = container.asset_store.path_for_uri(asset.uri)
    path.write_bytes(b"corrupt")
    with pytest.raises(CameraLockError) as error:
        svc.register_anchor(r.id, asset.id)
    assert error.value.code == "REFERENCE_ASSET_INVALID"
    assert svc.current_anchor(r.id) is None


def test_render_missing_binding_and_rig(container):
    svc = service(container)
    s = shot(container, project(container))
    for request, code in [
        (CameraLockRequest(enabled=True), "CAMERA_LOCK_NOT_BOUND"),
        (CameraLockRequest(enabled=True, rig_id="missing"), "CAMERA_RIG_NOT_FOUND"),
    ]:
        with pytest.raises(CameraLockError) as error:
            svc.validate_render_request(s.id, request)
        assert error.value.code == code


def test_anchor_changes_derive_staleness_and_mask_provenance(container):
    svc, s, r, _, _ = bound(container)
    mask = png(container, color="black")
    svc.bind_shot(s.id, r.id, face_policy="partial_allowed", edit_mask_asset_id=mask.id)
    result = container.shot_pipeline().render(s.id)
    attempt = container.shot_pipeline().get_attempt(result["generation_attempt_id"])
    before = json.dumps(attempt.payload, sort_keys=True)
    assert attempt.payload["mask_sha256"] == mask.sha256
    svc.register_anchor(r.id, png(container, color="red").id)
    assert svc.get_rig(r.id).revision == 1
    assert svc.attempt_camera_staleness(attempt) is True
    assert (
        json.dumps(container.shot_pipeline().get_attempt(attempt.id).payload, sort_keys=True)
        == before
    )


def test_qc_report_persistence(container):
    from creator_studio.domain.camera.models import CameraQCReport
    from creator_studio.domain.ids import new_id

    report = CameraQCReport(new_id(), "attempt", "candidate", {"face": 1.0}, "pass", [], "v1")
    with container.uow() as uow:
        uow.camera_qc_reports.add(report)
        uow.commit()
    with container.uow() as uow:
        assert uow.camera_qc_reports.get(report.id).to_dict() == report.to_dict()
        assert len(uow.camera_qc_reports.list_for_attempt("attempt")) == 1
