"""Live Stock MOSS-SFT smoke — Gate 1 (#B mandatory).

Requires SCENEWEAVER_MOSS_LIVE=1 + Comfy >= 0.42.1 (min e087d8f+) with MOSS weights.
When that env is set, missing Comfy / moss_image / weights must FAIL (not skip).
Entry: ``pnpm test:moss:live``.

Pass criteria:
  - Real PNG decodeable with width/height >= 512
  - Not near-black (Flux2 BF16 failure mode)
  - GenerationAttempt: provider=comfyui, model_id=moss_image_sft,
    capability=LayoutGuidedRender, workflow_template_id=moss_sft_v1,
    workflow_hash, seed
  - moss_caption_v1 prompt (no Anima safe/artist tokens)
  - Artifact PNG + manifest under docs/validation/moss-sft-gate1/
  - Same-seed replay restores capability/workflow snapshot

Prefer FP32 VAE (no --bf16-vae) on the Comfy host for first smoke.
"""

from __future__ import annotations

import io
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

import pytest
from PIL import Image

from creator_studio.application.projects.create_project import CreateProjectCommand
from creator_studio.domain.prompt import MOSS_COMPILER_SOURCE_REF, compute_prompt_hash
from creator_studio.infrastructure.container import Container, reset_container
from creator_studio.infrastructure.db.migrate import upgrade_head
from creator_studio.infrastructure.db.session import reset_engine
from creator_studio.infrastructure.settings import Settings, clear_settings_cache
from creator_studio.infrastructure.settings.config import REPO_ROOT

pytestmark = pytest.mark.skipif(
    os.environ.get("SCENEWEAVER_MOSS_LIVE", "").lower() not in {"1", "true", "yes"},
    reason="Set SCENEWEAVER_MOSS_LIVE=1 (Comfy >= 0.42.1 + MOSS weights) or run: pnpm test:moss:live",
)

_REQUIRED_UNET = "moss_image_sft_int8_convrot.safetensors"
_REQUIRED_CLIP = "qwen3.5_9b_w4a8_gptq.safetensors"
_REQUIRED_VAE = "flux2-vae_small.safetensors"
_MIN_EDGE = 512
_ARTIFACT_DIR = REPO_ROOT / "docs" / "validation" / "moss-sft-gate1"


def _comfy_get(url: str, path: str) -> object:
    with urllib.request.urlopen(f"{url.rstrip('/')}{path}", timeout=10) as resp:
        return json.loads(resp.read().decode())


def _require_moss_runtime(comfy_url: str) -> str:
    """Validate host for Gate 1. Returns comfyui_version. Failures are env-class (not SW)."""
    try:
        stats = _comfy_get(comfy_url, "/system_stats")
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        pytest.fail(f"ENV: ComfyUI unreachable at {comfy_url}: {exc}")

    system = stats.get("system") if isinstance(stats, dict) else {}
    version = str((system or {}).get("comfyui_version") or "")
    clip_info = _comfy_get(comfy_url, "/object_info/CLIPLoader")
    clip_types = []
    if isinstance(clip_info, dict) and "CLIPLoader" in clip_info:
        required = clip_info["CLIPLoader"].get("input", {}).get("required", {})
        type_opts = required.get("type")
        if isinstance(type_opts, list) and type_opts:
            clip_types = list(type_opts[0]) if isinstance(type_opts[0], list) else list(type_opts)
    if "moss_image" not in clip_types:
        # Expected FAIL on pre-native hosts (e.g. 0.31.1) — environment, not SceneWeaver.
        pytest.fail(
            "ENV: ComfyUI lacks CLIPLoader type=moss_image "
            f"(comfyui_version={version!r}). Upgrade to ComfyUI >= 0.42.1 (min e087d8f+)."
        )

    def _models(kind: str) -> list[str]:
        data = _comfy_get(comfy_url, f"/models/{kind}")
        return [str(x).replace("\\", "/") for x in (data if isinstance(data, list) else [])]

    diffusion = _models("diffusion_models")
    text_encoders = _models("text_encoders")
    vaes = _models("vae")
    missing = []
    if not any(_REQUIRED_UNET in p for p in diffusion):
        missing.append(f"diffusion_models/{_REQUIRED_UNET}")
    if not any(_REQUIRED_CLIP in p for p in text_encoders):
        missing.append(f"text_encoders/{_REQUIRED_CLIP}")
    if not any(_REQUIRED_VAE in p for p in vaes):
        missing.append(f"vae/{_REQUIRED_VAE}")
    if missing:
        pytest.fail(
            "ENV: MOSS weights missing on Comfy host (Comfy-Org/MOSS-Image): "
            + ", ".join(missing)
        )
    return version or "unknown"


def _assert_image_gate(png_bytes: bytes) -> tuple[int, int, float]:
    img = Image.open(io.BytesIO(png_bytes))
    img.load()
    width, height = img.size
    assert width >= _MIN_EDGE and height >= _MIN_EDGE, (
        f"image too small: {width}x{height} (need >= {_MIN_EDGE})"
    )
    gray = img.convert("L")
    hist = gray.histogram()
    total = sum(hist) or 1
    mean = sum(i * c for i, c in enumerate(hist)) / total
    assert 8.0 < mean < 248.0, f"image looks black/white washed (mean luma={mean:.1f})"
    return width, height, mean


def _write_gate_artifact(
    *,
    png_bytes: bytes,
    manifest: dict,
) -> Path:
    _ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    seed = manifest.get("seed", "unknown")
    image_file = str(manifest.get("image_file") or f"gate1_seed_{seed}.png")
    png_path = _ARTIFACT_DIR / image_file
    json_path = _ARTIFACT_DIR / f"gate1_seed_{seed}.manifest.json"
    manifest = {**manifest, "image_file": image_file}
    png_path.write_bytes(png_bytes)
    json_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    latest = _ARTIFACT_DIR / "LATEST.md"
    latest.write_text(
        f"# MOSS Gate 1 artifact\n\n"
        f"- status: `{manifest.get('status')}`\n"
        f"- PNG: `{png_path.name}`\n"
        f"- Manifest: `{json_path.name}`\n"
        f"- Size: {manifest.get('width')}x{manifest.get('height')}\n"
        f"- SHA256: `{manifest.get('sha256')}`\n"
        f"- workflow_hash: `{manifest.get('workflow_hash')}`\n"
        f"- comfy_version: `{manifest.get('comfy_version')}`\n",
        encoding="utf-8",
    )
    return png_path


@pytest.fixture()
def live_container(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Container, str]:
    runtime = tmp_path / "runtime-moss-live"
    runtime.mkdir()
    db = runtime / "live.db"
    comfy_url = os.environ.get("SCENEWEAVER_COMFY_URL", "http://127.0.0.1:8188")
    monkeypatch.setenv("SCENEWEAVER_RUNTIME_DIR", str(runtime))
    monkeypatch.setenv("SCENEWEAVER_DATABASE_URL", f"sqlite:///{db}")
    # live-test: effective_image_backend() prefers bootstrap env over user settings store.
    monkeypatch.setenv("SCENEWEAVER_ENVIRONMENT", "live-test")
    monkeypatch.setenv("SCENEWEAVER_IMAGE_BACKEND", "comfy")
    monkeypatch.setenv("SCENEWEAVER_COMFY_URL", comfy_url)
    monkeypatch.setenv("SCENEWEAVER_IMAGE_TAGGER", "off")
    # First MOSS load (UNET + Qwen3.5 TE) can exceed the default 300s poll window.
    monkeypatch.setenv("SCENEWEAVER_COMFY_POLL_TIMEOUT_SECONDS", "1200")
    clear_settings_cache()
    reset_engine()
    reset_container()
    settings = Settings()
    assert settings.image_backend == "comfy"
    assert settings.allows_test_control
    upgrade_head(settings.sqlalchemy_url())
    reset_engine()
    version = _require_moss_runtime(comfy_url)
    container = Container(settings)
    assert container.settings_service().effective_image_backend() == "comfy"
    return container, version


def test_moss_sft_live_smoke_provenance_and_replay(
    live_container: tuple[Container, str],
) -> None:
    c, comfy_version = live_container
    project = c.create_project().execute(CreateProjectCommand(title="MOSS Live Smoke"))
    char = c.create_character().execute("LiveMoss")
    scene = c.create_scene().execute(project.id, "Studio")
    beat = c.create_beat().execute(scene.id, intent="portrait", speaker_id=char.id)
    pipe = c.shot_pipeline()
    shot = pipe.plan_shot(beat.id)
    pipe.update_shot(
        shot.id,
        {
            "capability": "LayoutGuidedRender",
            "identity_tags": ["1girl", "long hair", "brown eyes"],
            "outfit_tags": "simple blouse",
            "expression": {"id": "neutral"},
            "pose": {"id": "standing"},
            "camera": {"shot": "medium", "angle": "eye_level"},
            "background": "plain studio backdrop",
        },
    )
    draft = c.prompt_draft_service().ensure_for_shot(shot.id)
    assert draft.source_ref == MOSS_COMPILER_SOURCE_REF
    for marker in ("safe", "@fuzichoco", "@rella", "score_9"):
        assert marker not in draft.rendered_base_positive

    seed = 12345
    rendered = pipe.render(shot.id, seed=seed)
    assert rendered["output_asset_ids"]
    attempt = pipe.get_attempt(rendered["generation_attempt_id"])
    assert attempt.seed == seed
    assert attempt.workflow_hash
    assert attempt.payload["capability"] == "LayoutGuidedRender"
    assert attempt.payload["model_id"] == "moss_image_sft"
    assert attempt.payload["provider"] == "comfyui"
    assert attempt.payload["render_snapshot"]["workflow_template_id"] == "moss_sft_v1"
    assert attempt.payload["source_ref"] == MOSS_COMPILER_SOURCE_REF
    for marker in ("safe", "@fuzichoco", "@rella"):
        assert marker not in attempt.payload["final_positive_prompt"]

    asset_id = rendered["output_asset_ids"][0]
    with c.uow() as uow:
        asset = uow.assets.get(asset_id)
        assert asset is not None
        uri = asset.uri
        sha256 = asset.sha256
        mime = asset.mime
    data = c.asset_store.path_for_uri(uri).read_bytes()
    width, height, mean = _assert_image_gate(data)
    prompt_hash = attempt.payload.get("prompt_hash") or compute_prompt_hash(
        attempt.payload.get("final_positive_prompt") or draft.rendered_base_positive,
        attempt.payload.get("final_negative_prompt") or draft.rendered_base_negative,
    )
    image_file = f"gate1_seed_{seed}.png"
    artifact = _write_gate_artifact(
        png_bytes=data,
        manifest={
            "gate": "moss-sft-gate1",
            "status": "passed",
            "provider": "comfyui",
            "capability": "LayoutGuidedRender",
            "model_id": "moss_image_sft",
            "workflow_template_id": "moss_sft_v1",
            "workflow_hash": attempt.workflow_hash,
            "seed": seed,
            "prompt_hash": prompt_hash,
            "width": width,
            "height": height,
            "mime": mime or "image/png",
            "sha256": sha256,
            "external_job_ref": attempt.payload.get("external_job_ref")
            or rendered.get("external_job_ref"),
            "comfy_version": comfy_version,
            "image_file": image_file,
            "mean_luma": round(mean, 2),
            "source_ref": draft.source_ref,
            "asset_id": asset_id,
            "generation_attempt_id": rendered["generation_attempt_id"],
        },
    )
    assert artifact.exists()

    replayed = pipe.replay(rendered["generation_attempt_id"], seed_mode="same")
    replay_attempt = pipe.get_attempt(replayed["generation_attempt_id"])
    assert replay_attempt.payload["capability"] == "LayoutGuidedRender"
    assert replay_attempt.payload["model_id"] == "moss_image_sft"
    assert replay_attempt.payload["render_snapshot"]["workflow_template_id"] == "moss_sft_v1"
    assert replay_attempt.seed == seed
    assert replay_attempt.workflow_hash
