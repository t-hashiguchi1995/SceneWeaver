"""Phase 1–2 formal live — Quick Studio → Comfy → PNG → provenance → Adopt(copy).

Entry: ``pnpm test:quick-studio:live``

PASS:
  - PoseControlledRender via Scratch Studio apply_pose (Shisei pack)
  - Real PNG decodeable ≥512
  - Attempt + asset pose_provenance (pose_id/view/sha256/flipped)
  - Model / seed / capability / workflow present
  - materialize copies same output_asset_ids (no rerender)
"""

from __future__ import annotations

import io
import json
import os
import subprocess
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pytest

from creator_studio.application.studio.scratch import ScratchStudioService
from creator_studio.domain.ids import CharacterId
from creator_studio.domain.wardrobe import OutfitProfile
from creator_studio.infrastructure.container import Container, reset_container
from creator_studio.infrastructure.db.migrate import upgrade_head
from creator_studio.infrastructure.db.session import reset_engine
from creator_studio.infrastructure.settings import Settings, clear_settings_cache
from creator_studio.infrastructure.settings.config import REPO_ROOT
from tests.live.anima_character_semantics import GATE26_PRIMARY
from tests.live.test_moss_sft_live import _assert_image_gate

pytestmark = pytest.mark.skipif(
    os.environ.get("SCENEWEAVER_ANIMA_LIVE", "").lower() not in {"1", "true", "yes"}
    and os.environ.get("SCENEWEAVER_QUICK_STUDIO_LIVE", "").lower() not in {"1", "true", "yes"},
    reason="Set SCENEWEAVER_QUICK_STUDIO_LIVE=1 (or SCENEWEAVER_ANIMA_LIVE=1) "
    "or run: pnpm test:quick-studio:live",
)

_ARTIFACT_DIR = REPO_ROOT / "docs" / "validation" / "quick-studio-phase1"
_MIN_EDGE = 512
_REQUIRED_CKPT = "anima_baseV10.safetensors"
_REQUIRED_LLLITE = "anima-lllite-pose-1.safetensors"
_SEED = 424242


def _git_commit() -> str:
    try:
        return (
            subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=REPO_ROOT,
                stderr=subprocess.DEVNULL,
            )
            .decode()
            .strip()
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def _comfy_get(url: str, path: str) -> object:
    with urllib.request.urlopen(f"{url.rstrip('/')}{path}", timeout=10) as resp:
        return json.loads(resp.read().decode())


def _require_pose_runtime(comfy_url: str) -> str:
    try:
        stats = _comfy_get(comfy_url, "/system_stats")
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        pytest.fail(f"ENV: ComfyUI unreachable at {comfy_url}: {exc}")
    system = stats.get("system") if isinstance(stats, dict) else {}
    version = str((system or {}).get("comfyui_version") or "")

    ckpts = [str(x).replace("\\", "/") for x in (_comfy_get(comfy_url, "/models/checkpoints") or [])]
    if not any(_REQUIRED_CKPT in p for p in ckpts):
        pytest.fail(f"ENV: missing checkpoint {_REQUIRED_CKPT}")

    patches = [str(x).replace("\\", "/") for x in (_comfy_get(comfy_url, "/models/model_patches") or [])]
    if not any(_REQUIRED_LLLITE in p for p in patches):
        pytest.fail(f"ENV: missing model_patch {_REQUIRED_LLLITE}")

    info = _comfy_get(comfy_url, "/object_info/AnimaLLLiteApply")
    if not isinstance(info, dict) or "AnimaLLLiteApply" not in info:
        pytest.fail("ENV: AnimaLLLiteApply node missing")
    return version or "unknown"


@pytest.fixture()
def live_container(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Container, str]:
    runtime = tmp_path / "runtime-quick-studio-live"
    runtime.mkdir()
    db = runtime / "live.db"
    comfy_url = os.environ.get("SCENEWEAVER_COMFY_URL", "http://127.0.0.1:8188")
    monkeypatch.setenv("SCENEWEAVER_RUNTIME_DIR", str(runtime))
    monkeypatch.setenv("SCENEWEAVER_DATABASE_URL", f"sqlite:///{db}")
    monkeypatch.setenv("SCENEWEAVER_ENVIRONMENT", "live-test")
    monkeypatch.setenv("SCENEWEAVER_IMAGE_BACKEND", "comfy")
    monkeypatch.setenv("SCENEWEAVER_COMFY_URL", comfy_url)
    monkeypatch.setenv("SCENEWEAVER_IMAGE_TAGGER", "off")
    monkeypatch.setenv("SCENEWEAVER_COMFY_POLL_TIMEOUT_SECONDS", "1200")
    clear_settings_cache()
    reset_engine()
    reset_container()
    settings = Settings()
    upgrade_head(settings.sqlalchemy_url())
    reset_engine()
    version = _require_pose_runtime(comfy_url)
    return Container(settings), version


def test_quick_studio_anima_pose_live(live_container: tuple[Container, str]) -> None:
    c, comfy_version = live_container
    sem = GATE26_PRIMARY[0]  # C01 リゼ — reuse Gate 2.6 identity
    poses = c.reference_pose_service().list_summaries()
    assert len(poses) >= 1
    pose = poses[0]
    pose_id = pose["id"]
    # Prefer diag when available (angle selection path)
    pose_view = "diag" if "diag" in (pose.get("available_views") or []) else pose["default_view"]

    char = c.create_character().execute(sem["display_name"])
    c.update_visual_identity().execute(
        char.id,
        {
            "identity_tags": list(sem["identity_tags"]),
            "character_name": sem["character_name"],
            "franchise": sem["franchise"],
            "hair": sem["identity_tags"][0] if sem["identity_tags"] else "",
        },
    )
    outfit = OutfitProfile.create(
        f"{sem['display_name']} Outfit A",
        character_id=CharacterId(char.id),
        semantic={"garment_description": sem["outfit_tags"]},
    )
    with c.uow() as uow:
        uow.outfit_profiles.add(outfit)
        uow.commit()

    studio = ScratchStudioService(c)
    session = studio.create_session(
        character_id=char.id,
        outfit_profile_id=outfit.id,
        model_profile="anima",
    )
    shot_id = session["shot_id"]
    assert session["lifecycle"] == "draft"
    assert session["model_profile"] == "anima"

    applied = studio.apply_pose(
        shot_id,
        pose_id=pose_id,
        pose_view=pose_view,
        flipped=False,
        control_strength=1.0,
    )
    snap = applied["pose_provenance"]
    assert snap["pose_id"] == pose_id
    assert snap["pose_view"] == pose_view
    assert snap["pose_method"] == "reference_image"
    assert snap["pose_asset_sha256"]
    assert applied["render_spec"]["capability"] == "PoseControlledRender"
    assert str(applied["render_spec"].get("pose_asset_uri") or "").startswith("asset://")

    pipe = c.shot_pipeline()
    pose_uri = applied["render_spec"]["pose_asset_uri"]
    result = pipe.render(
        shot_id,
        use_pose=True,
        pose_asset_uri=str(pose_uri),
        seed=_SEED,
    )
    studio.mark_generated(shot_id)
    assert result["output_asset_ids"]
    attempt_id = result["generation_attempt_id"]
    scratch_assets = list(result["output_asset_ids"])

    attempt = pipe.get_attempt(attempt_id)
    assert attempt.seed == _SEED
    payload = attempt.payload
    assert payload.get("capability") == "PoseControlledRender" or (
        payload.get("render_snapshot") or {}
    ).get("capability") == "PoseControlledRender"
    model_id = payload.get("model_id") or (payload.get("render_snapshot") or {}).get("model_id")
    workflow = payload.get("workflow_template_id") or (payload.get("render_snapshot") or {}).get(
        "workflow_template_id"
    )
    assert model_id == "anima_pose" or str(model_id).startswith("anima")
    assert "anima_pose" in str(workflow)
    pose_prov = payload.get("pose_provenance") or {}
    assert pose_prov.get("pose_id") == pose_id
    assert pose_prov.get("pose_view") == pose_view
    assert pose_prov.get("pose_asset_sha256") == snap["pose_asset_sha256"]

    asset_id = scratch_assets[0]
    with c.uow() as uow:
        from creator_studio.domain.ids import AssetId

        asset = uow.assets.get(AssetId(asset_id))
        assert asset is not None
        png_uri = asset.uri
        asset_sha = asset.sha256
        asset_prov = dict(asset.provenance or {})
    png_bytes = c.asset_store.path_for_uri(png_uri).read_bytes()
    width, height, mean = _assert_image_gate(png_bytes)
    assert width >= _MIN_EDGE and height >= _MIN_EDGE
    assert asset_prov.get("pose_provenance", {}).get("pose_asset_sha256") == snap[
        "pose_asset_sha256"
    ]

    adopted = studio.materialize_to_story(shot_id, generation_attempt_id=attempt_id)
    assert adopted["lifecycle"] == "adopted"
    assert adopted["output_asset_ids"] == scratch_assets
    formal_id = adopted["formal_shot_id"]
    assert formal_id
    formal = pipe.get_shot(formal_id)
    assert formal.render_spec.get("_adopted_from_scratch_shot_id") == shot_id
    assert "_studio" not in formal.render_spec

    _ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    png_path = _ARTIFACT_DIR / f"quick_studio_{pose_id}_{pose_view}_seed{_SEED}.png"
    png_path.write_bytes(png_bytes)
    manifest = {
        "status": "PASS",
        "gate": "quick-studio-phase1",
        "git_commit": _git_commit(),
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "comfy_version": comfy_version,
        "character": sem["display_name"],
        "fixture_id": sem["fixture_id"],
        "outfit_profile_id": outfit.id,
        "model_profile": "anima",
        "capability": "PoseControlledRender",
        "model_id": model_id,
        "workflow_template_id": workflow,
        "seed": _SEED,
        "pose_id": pose_id,
        "pose_view": pose_view,
        "pose_asset_sha256": snap["pose_asset_sha256"],
        "generation_attempt_id": attempt_id,
        "scratch_shot_id": shot_id,
        "formal_shot_id": formal_id,
        "output_asset_ids": scratch_assets,
        "materialize": "copy_generation_state",
        "width": width,
        "height": height,
        "mean_luma": mean,
        "sha256": asset_sha,
        "image_file": png_path.name,
        "workflow_hash": result.get("workflow_hash"),
    }
    man_path = _ARTIFACT_DIR / f"quick_studio_{pose_id}_{pose_view}_seed{_SEED}.manifest.json"
    man_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (_ARTIFACT_DIR / "SUMMARY.md").write_text(
        "\n".join(
            [
                "# Quick Studio Phase 1–2 live",
                "",
                f"- status: `PASS`",
                f"- commit: `{manifest['git_commit']}`",
                f"- comfy: `{comfy_version}`",
                f"- character: {sem['display_name']} ({sem['fixture_id']})",
                f"- pose: `{pose_id}` / `{pose_view}`",
                f"- capability: PoseControlledRender / model `{model_id}`",
                f"- seed: `{_SEED}`",
                f"- PNG: `{png_path.name}` ({width}x{height})",
                f"- pose_asset_sha256: `{snap['pose_asset_sha256']}`",
                f"- materialize: copy — formal `{formal_id}` keeps same asset IDs",
                "",
                "## Vertical slice",
                "",
                "```text",
                "/studio session",
                "→ Character + OutfitProfile + Anima",
                "→ Shisei Pose + angle",
                "→ PoseControlledRender (Comfy)",
                "→ PNG ≥512",
                "→ provenance (model/seed/pose sha)",
                "→ Adopt = copy (no rerender)",
                "```",
                "",
            ]
        ),
        encoding="utf-8",
    )
