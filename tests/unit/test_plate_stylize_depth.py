from __future__ import annotations

import pytest

from creator_studio.application.workflows import WorkflowCompiler, WorkflowValidationError
from creator_studio.infrastructure.workflows.loader import WorkflowTemplateLoader


def slots(**overrides):
    values = dict(
        source_image="asset://source.png",
        depth_image="asset://depth.png",
        positive="anime room",
        negative="people",
        steps=30,
        cfg=4,
        denoise=0.7,
        depth_strength=1.15,
        candidate_count=1,
    )
    values.update(overrides)
    return values


def compile_slots(values, *, seed=20261161):
    return WorkflowCompiler().compile(
        WorkflowTemplateLoader().load("plate_stylize_depth_v1"),
        slots=values,
        seed=seed,
        model_id="anima_plate_stylize_depth",
        approved_model_ids={"anima_plate_stylize_depth"},
    )


def test_depth_template_identity():
    loader = WorkflowTemplateLoader()
    template = loader.load("plate_stylize_depth_v1")
    assert template.id == "plate_stylize_depth_v1"
    assert template.backend == "comfyui"
    assert template.capability == "DepthGuidedStylize"
    assert template.required_model_id == "anima_plate_stylize_depth"
    assert template.workflow_file == "workflows/comfy/plate_stylize_depth.api.json"
    assert template.outputs == {"images": ["90"]}
    assert "plate_stylize_depth_v1" in loader.list_ids()


@pytest.mark.parametrize("candidate_count", [1, 4])
def test_depth_uses_encoded_source_and_depth_patch(candidate_count):
    values = slots(
        candidate_count=candidate_count, steps=24, cfg=5, denoise=0.6, depth_strength=0.9
    )
    graph = compile_slots(values, seed=12345).graph
    assert graph["102"]["class_type"] == "VAEEncode"
    assert graph["102"]["inputs"] == {"pixels": ["100", 0], "vae": ["15", 0]}
    assert graph["103"]["class_type"] == "RepeatLatentBatch"
    assert graph["103"]["inputs"] == {"samples": ["102", 0], "amount": candidate_count}
    assert graph["12"]["class_type"] == "KSampler"
    sampler = graph["12"]["inputs"]
    assert sampler["latent_image"] == ["103", 0]
    assert sampler["model"] == ["71", 0]
    for name in ("denoise", "steps", "cfg"):
        assert sampler[name] == values[name]
    assert sampler["seed"] == 12345
    assert sampler["positive"] == ["6", 0]
    assert sampler["negative"] == ["7", 0]
    assert graph["6"]["inputs"]["text"] == values["positive"]
    assert graph["7"]["inputs"]["text"] == values["negative"]
    assert graph["71"]["class_type"] == "AnimaLLLiteApply"
    assert graph["71"]["inputs"] == {
        "model": ["47", 0],
        "model_patch": ["72", 0],
        "image": ["101", 0],
        "strength": values["depth_strength"],
        "start_percent": 0.0,
        "end_percent": 1.0,
    }
    assert graph["72"]["class_type"] == "ModelPatchLoader"
    assert graph["72"]["inputs"]["name"] == "anima-lllite-depth-1.safetensors"
    for node, name in (("100", "source_image"), ("101", "depth_image")):
        assert graph[node]["class_type"] == "LoadImage"
        assert graph[node]["inputs"]["image"] == values[name]
    assert not any(
        n["class_type"] in {"EmptyLatentImage", "VAEEncodeForInpaint"} for n in graph.values()
    )


@pytest.mark.parametrize(
    "missing", ["source_image", "depth_image", "positive", "negative", "steps", "cfg", "denoise"]
)
def test_depth_required_slots(missing):
    values = slots()
    values.pop(missing)
    with pytest.raises(WorkflowValidationError, match="missing required slot"):
        compile_slots(values)


def test_depth_image_is_required():
    values = slots()
    values.pop("depth_image")
    with pytest.raises(WorkflowValidationError, match="missing required slot"):
        compile_slots(values)


# Denoise range validation currently applies only to PlateStylize. Supporting
# DepthGuidedStylize range validation is a follow-up requiring a validator change.
def test_denoise_is_required():
    values = slots()
    values.pop("denoise")
    with pytest.raises(WorkflowValidationError, match="missing required slot"):
        compile_slots(values)


def original_slots():
    return dict(
        source_image="asset://source.png",
        positive="anime room",
        negative="people",
        steps=30,
        cfg=4,
        denoise=0.55,
        candidate_count=4,
    )


def compile_original(values):
    return WorkflowCompiler().compile(
        WorkflowTemplateLoader().load("plate_stylize_v1"),
        slots=values,
        seed=20261161,
        model_id="anima_plate_stylize",
        approved_model_ids={"anima_plate_stylize"},
    )


def test_original_plate_stylize_remains_unpatched():
    graph = compile_original(original_slots()).graph
    assert graph["12"]["inputs"]["model"] == ["47", 0]
    assert graph["12"]["inputs"]["denoise"] == 0.55
    assert graph["103"]["inputs"]["amount"] == 4
    assert not any(n["class_type"] == "AnimaLLLiteApply" for n in graph.values())


def test_original_plate_stylize_still_rejects_depth():
    values = original_slots()
    values["depth_image"] = "asset://depth.png"
    with pytest.raises(WorkflowValidationError, match="depth ControlNet unavailable"):
        compile_original(values)


def test_depth_and_original_templates_are_distinct():
    loader = WorkflowTemplateLoader()
    original = loader.load("plate_stylize_v1")
    depth = loader.load("plate_stylize_depth_v1")
    assert original.id != depth.id
    assert original.workflow_file != depth.workflow_file
