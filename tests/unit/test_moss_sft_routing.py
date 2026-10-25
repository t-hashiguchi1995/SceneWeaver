"""Stock MOSS-SFT is LayoutGuidedRender; Anima keeps BaseRender."""

from __future__ import annotations

import json

from creator_studio.adapters.image import ComfyImageBackend, FakeImageBackend
from creator_studio.application.projects.create_project import CreateProjectCommand
from creator_studio.application.prompt.renderer import PromptRenderer
from creator_studio.application.workflows import WorkflowCompiler
from creator_studio.domain.prompt import MOSS_COMPILER_SOURCE_REF
from creator_studio.infrastructure.container import Container
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
    sampler = next(n for n in graph.values() if n["class_type"] == "KSampler")
    # OpenMOSS reference preset (not Comfy-Org fast 25/er_sde/simple).
    assert sampler["inputs"]["steps"] == 50
    assert sampler["inputs"]["cfg"] == 3.0
    assert sampler["inputs"]["sampler_name"] == "euler"
    assert sampler["inputs"]["scheduler"] == "sgm_uniform"


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
    assert compiled.graph["9"]["inputs"]["scheduler"] == "sgm_uniform"
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


_ANIMA_POLLUTION = ("safe", "@fuzichoco", "@rella", "score_9", "masterpiece", "year 2025")


def _assert_no_anima_pollution(text: str) -> None:
    for marker in _ANIMA_POLLUTION:
        assert marker not in text, f"unexpected Anima token {marker!r} in {text!r}"


def test_moss_caption_has_no_anima_pollution() -> None:
    rendered = PromptRenderer().render_for_capability(
        "LayoutGuidedRender",
        {
            "identity_tags": ["1girl", "silver_hair"],
            "outfit_tags": "school uniform",
            "expression": {"id": "smile"},
            "pose": {"id": "standing"},
            "camera": {"shot": "medium", "angle": "eye_level"},
            # Anima profile must be ignored on MOSS path.
            "prompt_profile_id": "anima_story_panel",
            "content_rating": "general",
        },
    )
    assert rendered.source_ref == MOSS_COMPILER_SOURCE_REF
    assert "Illustration of" in rendered.positive
    assert "silver_hair" in rendered.positive
    assert "school uniform" in rendered.positive
    _assert_no_anima_pollution(rendered.positive)
    assert "nsfw" in rendered.negative


def test_moss_adult_negative_omits_nsfw() -> None:
    rendered = PromptRenderer().render_moss({"content_rating": "adult", "identity_tags": ["1girl"]})
    assert "nsfw" not in rendered.negative
    _assert_no_anima_pollution(rendered.positive)


def test_layout_guided_shot_prompt_and_provenance(container: Container) -> None:
    project = container.create_project().execute(CreateProjectCommand(title="MOSS Fake"))
    char = container.create_character().execute("MossChar")
    scene = container.create_scene().execute(project.id, "Cafe")
    beat = container.create_beat().execute(scene.id, intent="sit", speaker_id=char.id)
    pipe = container.shot_pipeline()
    shot = pipe.plan_shot(beat.id)
    pipe.update_shot(
        shot.id,
        {
            "capability": "LayoutGuidedRender",
            "identity_tags": ["1girl", "blue_eyes"],
            "outfit_tags": "hoodie",
        },
    )
    drafts = container.prompt_draft_service()
    draft = drafts.ensure_for_shot(shot.id)
    assert draft.source_ref == MOSS_COMPILER_SOURCE_REF
    _assert_no_anima_pollution(draft.rendered_base_positive)

    rendered = pipe.render(shot.id, seed=42)
    attempt = pipe.get_attempt(rendered["generation_attempt_id"])
    assert attempt.payload["capability"] == "LayoutGuidedRender"
    assert attempt.payload["model_id"] == "moss_image_sft"
    assert attempt.payload.get("provider") == "fake"
    assert attempt.workflow_hash
    assert attempt.seed == 42
    _assert_no_anima_pollution(attempt.payload["final_positive_prompt"])
    snap = attempt.payload["render_snapshot"]
    assert snap["capability"] == "LayoutGuidedRender"
    assert snap["workflow_template_id"] == "moss_sft_v1"
    assert snap["model_id"] == "moss_image_sft"
