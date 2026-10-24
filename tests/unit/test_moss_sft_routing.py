"""Stock MOSS-SFT is LayoutGuidedRender; Anima keeps BaseRender."""

from __future__ import annotations

import json
from pathlib import Path

from creator_studio.adapters.image import ComfyImageBackend, FakeImageBackend
from creator_studio.application.workflows import WorkflowCompiler
from creator_studio.infrastructure.settings.config import REPO_ROOT
from creator_studio.infrastructure.workflows import WorkflowTemplateLoader, load_approved_model_ids
from creator_studio.infrastructure.workflows.registry_models import resolve_template_id_for_capability
from creator_studio.ports.image_backend import RenderPlanDTO


def test_base_render_stays_anima_layout_guided_is_moss() -> None:
    assert resolve_template_id_for_capability("BaseRender")[0] == "anima_base"
    model_id, template_path = resolve_template_id_for_capability("LayoutGuidedRender")
    assert model_id == "moss_image_sft"
    assert template_path.endswith("moss_sft.template.yaml")


def test_moss_api_graph_is_native_nodes_only() -> None:
    graph = json.loads((REPO_ROOT / "workflows/comfy/moss_sft.api.json").read_text())
    types = {node["class_type"] for node in graph.values()}
    # No OpenMOSS plugin loaders / ModelSamplingSD3.
    forbidden = {
        "MOSSImageHFLoader",
        "MOSS-Image HF Loader",
        "ModelSamplingSD3",
        "CheckpointLoaderSimple",
    }
    assert types.isdisjoint(forbidden)
    assert "UNETLoader" in types
    assert "CLIPLoader" in types
    assert "VAELoader" in types
    assert "SkipLayerGuidanceDiTSimple" in types
    assert "ModelSamplingAuraFlow" in types
    assert "EmptyFlux2LatentImage" in types
    clip = next(n for n in graph.values() if n["class_type"] == "CLIPLoader")
    assert clip["inputs"]["type"] == "moss_image"
    unet = next(n for n in graph.values() if n["class_type"] == "UNETLoader")
    assert "moss_image_sft" in unet["inputs"]["unet_name"]


def test_moss_template_compiles_and_backends_advertise_capability() -> None:
    loader = WorkflowTemplateLoader()
    compiler = WorkflowCompiler()
    approved = load_approved_model_ids()
    template = loader.load("moss_sft_v1")
    assert template.capability == "LayoutGuidedRender"
    compiled = compiler.compile(
        template,
        slots={"positive_prompt": "adult test character in a cafe", "negative_prompt": "bad"},
        seed=42,
        model_id="moss_image_sft",
        approved_model_ids=approved,
    )
    assert compiled.workflow_hash
    assert compiled.graph["4"]["inputs"]["text"] == "adult test character in a cafe"
    assert compiled.graph["9"]["inputs"]["seed"] == 42
    assert compiled.graph["8"]["inputs"]["shift"] == 5.0

    assert "LayoutGuidedRender" in FakeImageBackend().capabilities()
    assert "LayoutGuidedRender" in ComfyImageBackend("http://127.0.0.1:9").capabilities()
    assert "BaseRender" in FakeImageBackend().capabilities()


def test_fake_backend_validates_layout_guided_render() -> None:
    backend = FakeImageBackend()
    plan = RenderPlanDTO(
        capability="LayoutGuidedRender",
        template_id="moss_sft_v1",
        seed=7,
        slots={"positive_prompt": "studio portrait", "negative_prompt": "blur"},
    )
    result = backend.validate(plan)
    assert result.ok, result.errors
