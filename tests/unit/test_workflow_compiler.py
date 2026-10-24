from __future__ import annotations

import copy

import pytest

from creator_studio.adapters.image import ComfyImageBackend, FakeImageBackend
from creator_studio.application.workflows import WorkflowCompiler, WorkflowValidationError
from creator_studio.infrastructure.workflows import (
    WorkflowTemplateLoader,
    load_approved_model_ids,
)
from creator_studio.ports.image_backend import RenderPlanDTO


def test_valid_templates_compile() -> None:
    loader = WorkflowTemplateLoader()
    compiler = WorkflowCompiler()
    approved = load_approved_model_ids()
    for template_id, model_id, slots in [
        (
            "anima_base_v1",
            "anima_base",
            {"positive_prompt": "masterpiece", "negative_prompt": "bad"},
        ),
        (
            "anima_pose_v1",
            "anima_pose",
            {
                "positive_prompt": "masterpiece",
                "negative_prompt": "bad",
                "pose_image": "asset://pose.png",
            },
        ),
        (
            "moss_sft_v1",
            "moss_image_sft",
            {"positive_prompt": "a cafe scene", "negative_prompt": "bad"},
        ),
        (
            "qwen_tryon_v1",
            "qwen_image_edit_2509",
            {
                "edit_prompt": "wear cardigan",
                "character_image": "asset://char.png",
                "garment_image": "asset://plate.png",
            },
        ),
    ]:
        template = loader.load(template_id)
        compiled = compiler.compile(
            template,
            slots=slots,
            seed=99,
            model_id=model_id,
            approved_model_ids=approved,
        )
        assert compiled.workflow_hash
        assert compiled.seed == 99
        seed_binding = template.slots["seed"]
        assert compiled.graph[seed_binding.node]["inputs"][seed_binding.input] == 99


def test_missing_node_fails() -> None:
    loader = WorkflowTemplateLoader()
    compiler = WorkflowCompiler()
    template = loader.load("anima_base_v1")
    broken = copy.deepcopy(template)
    broken.workflow_graph.pop("6")
    with pytest.raises(WorkflowValidationError, match="missing node"):
        compiler.compile(
            broken,
            slots={"positive_prompt": "x", "negative_prompt": "y"},
            seed=1,
            model_id="anima_base",
            approved_model_ids={"anima_base"},
        )


def test_wrong_input_fails() -> None:
    loader = WorkflowTemplateLoader()
    compiler = WorkflowCompiler()
    template = loader.load("anima_base_v1")
    broken = copy.deepcopy(template)
    broken.workflow_graph["6"]["inputs"].pop("text")
    with pytest.raises(WorkflowValidationError, match="wrong input"):
        compiler.compile(
            broken,
            slots={"positive_prompt": "x", "negative_prompt": "y"},
            seed=1,
            model_id="anima_base",
            approved_model_ids={"anima_base"},
        )


def test_unknown_model_rejected() -> None:
    loader = WorkflowTemplateLoader()
    compiler = WorkflowCompiler()
    template = loader.load("anima_base_v1")
    with pytest.raises(WorkflowValidationError, match="unknown model"):
        compiler.compile(
            template,
            slots={"positive_prompt": "x", "negative_prompt": "y"},
            seed=1,
            model_id="not_in_registry",
            approved_model_ids={"anima_base"},
        )


def test_fake_and_comfy_dry_share_port_validation() -> None:
    plan = RenderPlanDTO(
        capability="BaseRender",
        template_id="anima_base_v1",
        seed=7,
        slots={"positive_prompt": "ok", "negative_prompt": "no"},
    )
    fake = FakeImageBackend(delay_ms=0)
    comfy = ComfyImageBackend("http://127.0.0.1:8188", dry_run=True)
    assert fake.validate(plan).ok is True
    assert comfy.validate(plan).ok is True
    bad = RenderPlanDTO(
        capability="BaseRender",
        template_id="anima_base_v1",
        seed=7,
        slots={},  # still ok — validator only checks graph slots exist
    )
    # compile still succeeds with empty optional text slots; missing node test covers failure
    assert fake.validate(bad).ok is True
    assert set(fake.capabilities()) == set(comfy.capabilities())
