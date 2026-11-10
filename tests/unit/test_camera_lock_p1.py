from __future__ import annotations

import io

import pytest
from PIL import Image, ImageDraw

from creator_studio.adapters.image.comfy_backend import ComfyImageBackend
from creator_studio.adapters.image.fake_backend import FakeImageBackend
from creator_studio.application.assets.store_asset import StoreBytesCommand
from creator_studio.application.camera.composition import (
    DEFAULT_FEATHER_PX,
    build_edit_mask,
    composite_protected_background,
    measure_protected_change,
)
from creator_studio.application.camera.face_visibility import FaceVisibilityResult
from creator_studio.application.camera.lock_service import CameraLockRequest, CameraLockService
from creator_studio.application.projects.create_project import CreateProjectCommand
from creator_studio.application.shots.pipeline import ShotPipeline
from creator_studio.application.workflows import WorkflowCompiler, WorkflowValidationError
from creator_studio.domain.asset import AssetKind
from creator_studio.domain.camera.errors import (
    CAMERA_LOCK_CAPABILITY_UNAVAILABLE,
    REFERENCE_ASSET_INVALID,
    CameraLockError,
)
from creator_studio.infrastructure.workflows.loader import WorkflowTemplateLoader
from creator_studio.infrastructure.workflows.registry_models import load_approved_model_ids
from creator_studio.ports.image_backend import GeneratedArtifact, RenderPlanDTO


class NoCameraBackend(FakeImageBackend):
    def capabilities(self):
        return super().capabilities() - {"CameraLockedRender"}


class Checker:
    def __init__(self, status):
        self.status = status

    def check(self, image_bytes):
        return FaceVisibilityResult(self.status, {"checker": "test"})


def png_bytes(size, color, *, rectangle=None, mode="RGB"):
    image = Image.new(mode, size, color)
    if rectangle:
        ImageDraw.Draw(image).rectangle(rectangle, fill="white")
    stream = io.BytesIO()
    image.save(stream, format="PNG")
    return stream.getvalue()


def store_png(container, data):
    return container.store_asset().execute(
        StoreBytesCommand(data, AssetKind.GENERATED, "image/png", "camera", "anchor.png")
    )


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


class CameraBackend(FakeImageBackend):
    def camera_lock_available(self) -> bool:
        return True

    def capabilities(self):
        return super().capabilities() | {"CameraLockedRender"}

    def collect(self, ref):
        plan = self._jobs[ref.ref]
        return [GeneratedArtifact(
            bytes_data=png_bytes((1536, 864), (30, 30, 200)),
            mime="image/png",
            metadata={
                "seed": plan.seed,
                "index": 0,
                "capability": "CameraLockedRender",
                "provider": "fake",
                "workflow_template_id": "camera_lock_inpaint_v1",
                "workflow_hash": "camhash123",
                "external_job_ref": ref.ref,
            },
        )]


def bound(container, *, anchor_size=(1536, 864), with_mask=True):
    p = project(container)
    s = shot(container, p)
    svc = CameraLockService(container.uow(), container.asset_store, Checker("full_visible"))
    rig = svc.create_rig(p.id, name="Studio", frame_width=1536, frame_height=864)
    anchor_bytes = png_bytes(anchor_size, "white")
    anchor = store_png(container, anchor_bytes)
    svc.register_anchor(rig.id, anchor.id)
    mask_bytes = png_bytes((1536, 864), "black", rectangle=(500, 250, 1000, 650))
    mask = store_png(container, mask_bytes) if with_mask else None
    svc.bind_shot(
        s.id, rig.id, face_policy="partial_allowed",
        edit_mask_asset_id=mask.id if mask else None,
    )
    pipeline = ShotPipeline(
        container.uow(), object(), CameraBackend(delay_ms=0), container.asset_store,
        camera_lock_service=svc,
    )
    return s, pipeline, anchor_bytes, mask_bytes


def test_composition_protects_outside_mask():
    anchor = png_bytes((96, 64), (200, 30, 30))
    generated = png_bytes((96, 64), (30, 30, 200))
    mask = png_bytes((96, 64), "black", rectangle=(32, 16, 63, 47), mode="L")
    out = composite_protected_background(anchor, generated, mask)
    assert measure_protected_change(anchor, out, mask) == 0.0
    with Image.open(io.BytesIO(out)) as image:
        assert image.getpixel((48, 32)) == (30, 30, 200)
        assert image.getpixel((0, 0)) == (200, 30, 30)
        erosion = DEFAULT_FEATHER_PX + 2
        for x in range(32 + erosion, 64 - erosion):
            for y in range(16 + erosion, 48 - erosion):
                assert image.getpixel((x, y)) == (30, 30, 200)


def test_composition_rejects_size_mismatch():
    with pytest.raises(ValueError, match="image size mismatch"):
        composite_protected_background(
            png_bytes((32, 32), "white"), png_bytes((16, 16), "blue"),
            png_bytes((32, 32), "black"),
        )


def test_build_edit_mask_dilation():
    mask = png_bytes((32, 32), "black", rectangle=(16, 16, 16, 16), mode="L")
    with Image.open(io.BytesIO(build_edit_mask(mask, dilation_px=2))) as image:
        assert image.size == (32, 32)
        assert image.mode == "L"
        assert {(x, y) for x in range(32) for y in range(32) if image.getpixel((x, y))} == {
            (x, y) for x in range(14, 19) for y in range(14, 19)
        }
    with Image.open(io.BytesIO(build_edit_mask(mask, dilation_px=0))) as image:
        with Image.open(io.BytesIO(mask)) as original:
            assert image.tobytes() == original.tobytes()


def camera_slots():
    return {
        "positive_prompt": "studio", "negative_prompt": "blur",
        "anchor_image": "asset://anchor.png", "edit_mask_image": "asset://mask.png",
    }


def test_workflow_compiler_required_slots():
    template = WorkflowTemplateLoader().load("camera_lock_inpaint_v1")
    slots = camera_slots()
    kwargs = dict(model_id="anima_camera_lock", approved_model_ids=load_approved_model_ids(), seed=1)
    compiled = WorkflowCompiler().compile(template, slots=slots, **kwargs)
    assert "anchor_image" in compiled.slots_applied
    del slots["edit_mask_image"]
    with pytest.raises(WorkflowValidationError, match="missing required slot: edit_mask_image"):
        WorkflowCompiler().compile(template, slots=slots, **kwargs)


def test_comfy_backend_camera_slot_validation(tmp_path):
    anchor_path = tmp_path / "anchor.png"
    mask_path = tmp_path / "mask.png"
    anchor_path.write_bytes(png_bytes((64, 64), "white"))
    mask_path.write_bytes(png_bytes((32, 32), "black"))

    class Store:
        def path_for_uri(self, uri):
            return {"asset://anchor.png": anchor_path, "asset://mask.png": mask_path}[uri]

    backend = ComfyImageBackend("http://127.0.0.1:9", asset_store=Store(), dry_run=True)

    def validate(slots):
        return backend.validate(RenderPlanDTO(
            capability="CameraLockedRender", template_id="camera_lock_inpaint_v1",
            seed=1, slots=slots,
        ))

    result = validate({**camera_slots(), "anchor_image": "https://example.com/x.png"})
    assert not result.ok
    assert any("REFERENCE_ASSET_INVALID" in e for e in result.errors)
    result = validate(camera_slots())
    assert not result.ok
    assert any("REFERENCE_ASSET_INVALID" in e for e in result.errors)
    mask_path.write_bytes(png_bytes((64, 64), "black"))
    assert validate(camera_slots()).ok


def test_pipeline_routes_camera_lock_with_capable_backend(container):
    s, pipeline, anchor, mask = bound(container)
    result = pipeline.render(s.id, camera_lock=CameraLockRequest(enabled=True))
    attempt = pipeline.get_attempt(result["generation_attempt_id"])
    assert attempt.payload["capability"] == "CameraLockedRender"
    assert attempt.payload["camera_lock_workflow_hash"] == "camhash123"
    with container.uow() as uow:
        asset = uow.assets.get(result["output_asset_ids"][0])
        out = container.asset_store.path_for_uri(asset.uri).read_bytes()
    with Image.open(io.BytesIO(out)) as image:
        assert image.getpixel((0, 0)) == (255, 255, 255)
        assert image.getpixel((750, 450)) == (30, 30, 200)
    assert measure_protected_change(anchor, out, mask) == 0.0


def test_pipeline_camera_lock_unavailable_with_fake_backend(container):
    s, _, _, _ = bound(container)
    with container.uow() as uow:
        count = len(uow.generation_attempts.list_for_shot(s.id))
    pipeline = ShotPipeline(
        container.uow(),
        container.llm(),
        NoCameraBackend(delay_ms=0),
        container.asset_store,
        container.prompts,
        container.prompt_renderer(),
        camera_lock_service=container.camera_lock_service(),
    )
    with pytest.raises(CameraLockError) as exc:
        pipeline.render(s.id, camera_lock=CameraLockRequest(enabled=True))
    assert exc.value.code == CAMERA_LOCK_CAPABILITY_UNAVAILABLE
    with container.uow() as uow:
        assert len(uow.generation_attempts.list_for_shot(s.id)) == count


def test_resolve_render_inputs_rejects_wrong_size_anchor(container):
    s, pipeline, _, _ = bound(container, anchor_size=(640, 360))
    with pytest.raises(CameraLockError) as exc:
        pipeline.render(s.id, camera_lock=CameraLockRequest(enabled=True))
    assert exc.value.code == REFERENCE_ASSET_INVALID


def test_render_requires_edit_mask(container):
    s, pipeline, _, _ = bound(container, with_mask=False)
    with pytest.raises(CameraLockError) as exc:
        pipeline.render(s.id, camera_lock=CameraLockRequest(enabled=True))
    assert exc.value.code == REFERENCE_ASSET_INVALID
