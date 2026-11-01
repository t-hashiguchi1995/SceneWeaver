"""A3 Pose Gallery Live — P01–P05 real Comfy generation.

Entry: ``pnpm test:pose-gallery:live``

P01 Prompt Pose · P02 Reference/LLLite · P03 Flip · P04 Character isolation · P05 Outfit isolation
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import subprocess
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
from PIL import Image, ImageDraw, ImageFont

from creator_studio.application.studio.scratch import ScratchStudioService
from creator_studio.domain.ids import CharacterId
from creator_studio.domain.wardrobe import OutfitProfile
from creator_studio.infrastructure.container import Container, reset_container
from creator_studio.infrastructure.db.migrate import upgrade_head
from creator_studio.infrastructure.db.session import reset_engine
from creator_studio.infrastructure.settings import Settings, clear_settings_cache
from creator_studio.infrastructure.settings.config import REPO_ROOT
from tests.live.anima_character_semantics import GATE27_PRIMARY
from tests.live.test_moss_sft_live import _assert_image_gate

pytestmark = pytest.mark.skipif(
    os.environ.get("SCENEWEAVER_POSE_GALLERY_LIVE", "").lower() not in {"1", "true", "yes"}
    and os.environ.get("SCENEWEAVER_ANIMA_LIVE", "").lower() not in {"1", "true", "yes"},
    reason="Set SCENEWEAVER_POSE_GALLERY_LIVE=1 or run: pnpm test:pose-gallery:live",
)

_ARTIFACT_DIR = REPO_ROOT / "docs" / "validation" / "pose-gallery-live"
_ADOPTED = REPO_ROOT / "docs" / "validation" / "anima-gate2_7" / "adopted_prompts"
_REQUIRED_CKPT = "anima_baseV10.safetensors"
_REQUIRED_LLLITE = "anima-lllite-pose-1.safetensors"
_POSE_ID = "sw-pose-0001"
_POSE_VIEW = "diag"
_DEFAULT_NEG = (
    "worst quality, low quality, score_1, score_2, score_3, blurry, jpeg artifacts, "
    "sepia, bad anatomy, bad hands, text, error, missing fingers, extra digit, "
    "fewer digits, cropped, signature, watermark, username, artist name"
)

# Fixed seeds for rematch comparability
_SEEDS = {
    "P01": 33001,
    "P02": 33002,
    "P03": 33003,
    "P04": 33004,
    "P05": 33005,
}

_A3_CHARS = {
    "C01": "C01_lize.anima.txt",
    "C07": "C07_tsubasa.anima.txt",
    "C10": "C10_firefly.anima.txt",
}

_OUTFIT_A = "royal blue and white dress, blue jacket, white blouse, silver crown"
_OUTFIT_B = (
    "red cardigan, white blouse, plaid skirt, loafers, school uniform, "
    "a3_outfit_b_marker"
)


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


def _load_adopted(fid: str) -> str:
    name = _A3_CHARS[fid]
    return (_ADOPTED / name).read_text(encoding="utf-8").strip()


def _sem(fid: str) -> dict[str, Any]:
    return next(s for s in GATE27_PRIMARY if s["fixture_id"] == fid)


def _inject_pose(adopted: str, pose_prompt: str) -> str:
    """Swap a trailing standing token for Gallery pose_prompt tags."""
    needle = ", standing,"
    if needle in adopted:
        return adopted.replace(needle, f", {pose_prompt},", 1)
    return f"{adopted}, {pose_prompt}"


def _swap_outfit(adopted: str, outfit: str) -> str:
    # Replace from crown/dress region or after identity → before expression
    for old in (
        "royal blue and white dress, blue jacket, white blouse",
        "sporty idol outfit, warm accent colors",
        "white shirt, black jacket, long sleeves",
    ):
        if old in adopted:
            return adopted.replace(old, outfit, 1)
    # Fallback: insert before expression cue
    for cue in (", calm expression,", ", confident smile,", ", slight smile,"):
        if cue in adopted:
            return adopted.replace(cue, f", {outfit}{cue}", 1)
    return f"{adopted}, {outfit}"


@pytest.fixture()
def live_container(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Container, str]:
    runtime = tmp_path / "runtime-pose-gallery-a3"
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
    return Container(settings), _require_pose_runtime(comfy_url)


def _seed_char_outfit(
    c: Container,
    fid: str,
    *,
    outfit_desc: str,
    outfit_title: str,
) -> tuple[str, str]:
    sem = _sem(fid)
    char = c.create_character().execute(f"{sem['display_name']} A3")
    c.update_visual_identity().execute(
        char.id,
        {
            "identity_tags": list(sem["identity_tags"]),
            "character_name": sem["character_name"],
            "franchise": sem["franchise"],
        },
    )
    outfit = OutfitProfile.create(
        outfit_title,
        character_id=CharacterId(char.id),
        semantic={"garment_description": outfit_desc},
    )
    with c.uow() as uow:
        uow.outfit_profiles.add(outfit)
        uow.commit()
    return char.id, outfit.id


def _write_case(
    case_id: str,
    *,
    png: bytes,
    manifest: dict[str, Any],
    checklist: list[str],
) -> None:
    d = _ARTIFACT_DIR / case_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "image.png").write_bytes(png)
    (d / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (d / "gt_checklist.md").write_text("\n".join(checklist) + "\n", encoding="utf-8")


def _contact_sheet(rows: list[dict[str, Any]]) -> None:
    thumb, pad, label_h, cols = 260, 8, 40, 3
    n = len(rows)
    rows_n = (n + cols - 1) // cols
    cell_w, cell_h = thumb, thumb + label_h
    sheet_w = cols * cell_w + (cols + 1) * pad
    sheet_h = rows_n * cell_h + (rows_n + 1) * pad
    sheet = Image.new("RGB", (sheet_w, sheet_h), (18, 18, 22))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 11)
    except OSError:
        font = ImageFont.load_default()
    for i, row in enumerate(rows):
        r, c = divmod(i, cols)
        x0 = pad + c * (cell_w + pad)
        y0 = pad + r * (cell_h + pad)
        img = Image.open(io.BytesIO(row["png"])).convert("RGB")
        img.thumbnail((thumb, thumb))
        sheet.paste(img, (x0 + (thumb - img.width) // 2, y0 + (thumb - img.height) // 2))
        draw.text(
            (x0 + 4, y0 + thumb + 4),
            row["label"][:42],
            fill=(230, 230, 235),
            font=font,
        )
    _ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    sheet.save(_ARTIFACT_DIR / "contact_sheet.png", format="PNG")


def test_pose_gallery_live_p01_to_p05(live_container: tuple[Container, str]) -> None:
    c, comfy_version = live_container
    commit = _git_commit()
    studio = ScratchStudioService(c)
    pipe = c.shot_pipeline()
    drafts = c.prompt_draft_service()
    _ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    detail = c.reference_pose_service().get_detail(_POSE_ID)
    assert detail is not None
    view = (detail.get("views") or {})[_POSE_VIEW]
    pose_prompt = str(view.get("prompt") or "")
    assert "hand on hip" in pose_prompt.lower() or "contrapposto" in pose_prompt.lower()

    sheet_rows: list[dict[str, Any]] = []
    case_rows: list[dict[str, Any]] = []

    def render_and_gate(
        shot_id: str,
        *,
        seed: int,
        use_pose: bool,
        pose_uri: str | None,
        positive: str,
        negative: str,
    ) -> tuple[dict[str, Any], bytes, dict[str, Any]]:
        drafts.update_edits(shot_id, positive, negative)
        result = pipe.render(
            shot_id,
            use_pose=use_pose,
            pose_asset_uri=pose_uri,
            seed=seed,
        )
        studio.mark_generated(shot_id)
        attempt = pipe.get_attempt(result["generation_attempt_id"])
        assert attempt.seed == seed
        asset_id = result["output_asset_ids"][0]
        with c.uow() as uow:
            a = uow.assets.get(asset_id)
            assert a is not None
            uri, sha = a.uri, a.sha256
        data = c.asset_store.path_for_uri(uri).read_bytes()
        width, height, mean = _assert_image_gate(data)
        assert hashlib.sha256(data).hexdigest() == sha
        return result, data, {
            "attempt": attempt,
            "sha256": sha,
            "width": width,
            "height": height,
            "mean_luma": mean,
            "asset_id": asset_id,
            "final_positive": attempt.payload.get("final_positive_prompt") or positive,
            "pose_prov": attempt.payload.get("pose_provenance") or {},
            "capability": attempt.payload.get("capability")
            or (attempt.payload.get("render_snapshot") or {}).get("capability"),
            "model_id": attempt.payload.get("model_id")
            or (attempt.payload.get("render_snapshot") or {}).get("model_id"),
            "workflow": attempt.payload.get("workflow_template_id")
            or (attempt.payload.get("render_snapshot") or {}).get("workflow_template_id"),
        }

    # ---- P01 Prompt Pose (Lize) ----
    print("\n=== P01 Prompt Pose ===", flush=True)
    char_p01, outfit_p01 = _seed_char_outfit(
        c, "C01", outfit_desc=_OUTFIT_A, outfit_title="Lize Royal A"
    )
    sess = studio.create_session(character_id=char_p01, outfit_profile_id=outfit_p01)
    shot = sess["shot_id"]
    applied = studio.apply_pose(
        shot,
        pose_id=_POSE_ID,
        pose_view=_POSE_VIEW,
        pose_method="prompt",
    )
    snap = applied["pose_provenance"]
    assert snap["pose_method"] == "prompt"
    assert not applied["render_spec"].get("pose_asset_uri")
    assert applied["render_spec"]["capability"] == "BaseRender"
    pos = _inject_pose(_load_adopted("C01"), pose_prompt)
    assert "hand on hip" in pos.lower() or "contrapposto" in pos.lower()
    assert "asset://" not in json.dumps(applied)
    _, png, meta = render_and_gate(
        shot,
        seed=_SEEDS["P01"],
        use_pose=False,
        pose_uri=None,
        positive=pos,
        negative=_DEFAULT_NEG,
    )
    assert meta["capability"] == "BaseRender"
    assert meta["pose_prov"].get("pose_method") == "prompt"
    assert "hand on hip" in meta["final_positive"].lower() or "contrapposto" in meta[
        "final_positive"
    ].lower()
    man = {
        "case": "P01",
        "title": "Prompt Pose",
        "character": "C01",
        "seed": _SEEDS["P01"],
        "pose_id": _POSE_ID,
        "pose_view": _POSE_VIEW,
        "pose_method": "prompt",
        "capability": meta["capability"],
        "model_id": meta["model_id"],
        "workflow_template_id": meta["workflow"],
        "sha256": meta["sha256"],
        "width": meta["width"],
        "height": meta["height"],
        "comfy_version": comfy_version,
        "commit": commit,
        "final_positive_prompt": meta["final_positive"],
        "pose_provenance": meta["pose_prov"],
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    _write_case(
        "P01",
        png=png,
        manifest=man,
        checklist=[
            "# P01 Prompt Pose — GT checklist",
            "",
            "- [ ] Pose cues from prompt visible (hand on hip / three-quarter / contrapposto)",
            "- [x] Auto: BaseRender + pose_method=prompt + pose tokens in final prompt",
            "- [x] Auto: no asset:// in session payload",
            "",
            "Notes: _human_",
            "",
        ],
    )
    sheet_rows.append({"png": png, "label": f"P01 prompt C01 s{_SEEDS['P01']}"})
    case_rows.append({"id": "P01", "status": "auto_pass", "sha": meta["sha256"][:12]})

    # ---- P02 Reference Pose / LLLite (Lize) ----
    print("\n=== P02 Reference Pose ===", flush=True)
    char_p02, outfit_p02 = _seed_char_outfit(
        c, "C01", outfit_desc=_OUTFIT_A, outfit_title="Lize Royal P02"
    )
    sess = studio.create_session(character_id=char_p02, outfit_profile_id=outfit_p02)
    shot = sess["shot_id"]
    applied = studio.apply_pose(
        shot, pose_id=_POSE_ID, pose_view=_POSE_VIEW, flipped=False, control_strength=1.0
    )
    snap = applied["pose_provenance"]
    assert snap["pose_method"] == "reference_image"
    assert snap["pose_asset_sha256"]
    pose_uri = applied["render_spec"]["pose_asset_uri"]
    assert str(pose_uri).startswith("asset://")
    p02_sha = snap["pose_asset_sha256"]
    pos = _load_adopted("C01")
    _, png, meta = render_and_gate(
        shot,
        seed=_SEEDS["P02"],
        use_pose=True,
        pose_uri=str(pose_uri),
        positive=pos,
        negative=_DEFAULT_NEG,
    )
    assert meta["capability"] == "PoseControlledRender"
    assert "anima_pose" in str(meta["workflow"])
    assert meta["pose_prov"].get("pose_asset_sha256") == p02_sha
    man = {
        "case": "P02",
        "title": "Reference Pose (LLLite)",
        "character": "C01",
        "seed": _SEEDS["P02"],
        "pose_id": _POSE_ID,
        "pose_view": _POSE_VIEW,
        "pose_method": "reference_image",
        "flipped": False,
        "control_strength": 1.0,
        "capability": meta["capability"],
        "model_id": meta["model_id"],
        "workflow_template_id": meta["workflow"],
        "sha256": meta["sha256"],
        "width": meta["width"],
        "height": meta["height"],
        "comfy_version": comfy_version,
        "commit": commit,
        "final_positive_prompt": meta["final_positive"],
        "pose_provenance": meta["pose_prov"],
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    _write_case(
        "P02",
        png=png,
        manifest=man,
        checklist=[
            "# P02 Reference Pose — GT checklist",
            "",
            "- [ ] Body pose leans toward reference (hand-on-hip / three-quarter)",
            "- [x] Auto: PoseControlledRender + anima_pose + pose_asset_sha256",
            "",
            "Notes: _human_",
            "",
        ],
    )
    sheet_rows.append({"png": png, "label": f"P02 ref C01 s{_SEEDS['P02']}"})
    case_rows.append({"id": "P02", "status": "auto_pass", "sha": meta["sha256"][:12]})

    # ---- P03 Flip ----
    print("\n=== P03 Flip ===", flush=True)
    char_p03, outfit_p03 = _seed_char_outfit(
        c, "C01", outfit_desc=_OUTFIT_A, outfit_title="Lize Royal P03"
    )
    sess = studio.create_session(character_id=char_p03, outfit_profile_id=outfit_p03)
    shot = sess["shot_id"]
    applied = studio.apply_pose(
        shot,
        pose_id=_POSE_ID,
        pose_view=_POSE_VIEW,
        flipped=True,
        control_strength=1.0,
    )
    snap = applied["pose_provenance"]
    assert snap["flipped"] is True
    assert snap["pose_asset_sha256"]
    assert snap["pose_asset_sha256"] != p02_sha
    pose_uri = applied["render_spec"]["pose_asset_uri"]
    _, png, meta = render_and_gate(
        shot,
        seed=_SEEDS["P03"],
        use_pose=True,
        pose_uri=str(pose_uri),
        positive=_load_adopted("C01"),
        negative=_DEFAULT_NEG,
    )
    assert meta["pose_prov"].get("flipped") is True
    man = {
        "case": "P03",
        "title": "Flip",
        "character": "C01",
        "seed": _SEEDS["P03"],
        "pose_id": _POSE_ID,
        "pose_view": _POSE_VIEW,
        "pose_method": "reference_image",
        "flipped": True,
        "pose_asset_sha256": snap["pose_asset_sha256"],
        "unflipped_pose_asset_sha256": p02_sha,
        "capability": meta["capability"],
        "model_id": meta["model_id"],
        "workflow_template_id": meta["workflow"],
        "sha256": meta["sha256"],
        "width": meta["width"],
        "height": meta["height"],
        "comfy_version": comfy_version,
        "commit": commit,
        "final_positive_prompt": meta["final_positive"],
        "pose_provenance": meta["pose_prov"],
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    _write_case(
        "P03",
        png=png,
        manifest=man,
        checklist=[
            "# P03 Flip — GT checklist",
            "",
            "- [ ] Mirrored relative to P02 reference lean (left/right hand/hip)",
            "- [x] Auto: flipped=true and pose_asset_sha256 ≠ unflipped",
            "",
            "Notes: _human_",
            "",
        ],
    )
    sheet_rows.append({"png": png, "label": f"P03 flip C01 s{_SEEDS['P03']}"})
    case_rows.append({"id": "P03", "status": "auto_pass", "sha": meta["sha256"][:12]})

    # ---- P04 Character isolation (same pose × C01/C07/C10) ----
    print("\n=== P04 Character isolation ===", flush=True)
    triggers = {
        "C01": ("lize helesta", "nijisanji"),
        "C07": ("ibuki tsubasa", "idolmaster"),
        "C10": ("firefly", "honkai"),
    }
    foreign = {
        "C01": ["ibuki tsubasa", "firefly (honkai"],
        "C07": ["lize helesta", "firefly (honkai"],
        "C10": ["lize helesta", "ibuki tsubasa"],
    }
    p04_pose_sha: str | None = None
    for fid in ("C01", "C07", "C10"):
        char_id, outfit_id = _seed_char_outfit(
            c, fid, outfit_desc=_sem(fid)["outfit_tags"], outfit_title=f"{fid} default"
        )
        sess = studio.create_session(character_id=char_id, outfit_profile_id=outfit_id)
        shot = sess["shot_id"]
        applied = studio.apply_pose(
            shot, pose_id=_POSE_ID, pose_view=_POSE_VIEW, flipped=False, control_strength=1.0
        )
        snap = applied["pose_provenance"]
        if p04_pose_sha is None:
            p04_pose_sha = snap["pose_asset_sha256"]
        else:
            assert snap["pose_asset_sha256"] == p04_pose_sha
        pose_uri = applied["render_spec"]["pose_asset_uri"]
        pos = _load_adopted(fid)
        for t in triggers[fid]:
            assert t in pos.lower()
        for bad in foreign[fid]:
            assert bad not in pos.lower()
        _, png, meta = render_and_gate(
            shot,
            seed=_SEEDS["P04"],
            use_pose=True,
            pose_uri=str(pose_uri),
            positive=pos,
            negative=_DEFAULT_NEG,
        )
        for t in triggers[fid]:
            assert t in meta["final_positive"].lower()
        for bad in foreign[fid]:
            assert bad not in meta["final_positive"].lower()
        assert meta["pose_prov"].get("pose_asset_sha256") == p04_pose_sha
        case_dir = f"P04_{fid}"
        man = {
            "case": "P04",
            "subcase": fid,
            "title": "Character isolation",
            "character": fid,
            "seed": _SEEDS["P04"],
            "pose_id": _POSE_ID,
            "pose_view": _POSE_VIEW,
            "shared_pose_asset_sha256": p04_pose_sha,
            "capability": meta["capability"],
            "sha256": meta["sha256"],
            "width": meta["width"],
            "height": meta["height"],
            "comfy_version": comfy_version,
            "commit": commit,
            "final_positive_prompt": meta["final_positive"],
            "pose_provenance": meta["pose_prov"],
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }
        _write_case(
            case_dir,
            png=png,
            manifest=man,
            checklist=[
                f"# P04 Character isolation — {fid}",
                "",
                "- [ ] Output is the target character (not pose thumbnail person)",
                "- [ ] No cross-character hair/outfit bleed from other P04 siblings",
                "- [x] Auto: shared pose_asset_sha256; trigger present; foreign triggers absent",
                "",
                "Notes: _human_",
                "",
            ],
        )
        sheet_rows.append(
            {"png": png, "label": f"P04 {fid} s{_SEEDS['P04']}"}
        )
    case_rows.append({"id": "P04", "status": "auto_pass", "sha": "see P04_*"})

    # ---- P05 Outfit isolation (same pose × Outfit A/B) ----
    print("\n=== P05 Outfit isolation ===", flush=True)
    char_p05, outfit_a = _seed_char_outfit(
        c, "C01", outfit_desc=_OUTFIT_A, outfit_title="Lize Outfit A"
    )
    outfit_b = OutfitProfile.create(
        "Lize Outfit B",
        character_id=CharacterId(char_p05),
        semantic={"garment_description": _OUTFIT_B},
    )
    with c.uow() as uow:
        uow.outfit_profiles.add(outfit_b)
        uow.commit()

    shared_pose_sha: str | None = None
    for label, outfit_id, garment in (
        ("A", outfit_a, _OUTFIT_A),
        ("B", outfit_b.id, _OUTFIT_B),
    ):
        sess = studio.create_session(character_id=char_p05, outfit_profile_id=outfit_id)
        shot = sess["shot_id"]
        applied = studio.apply_pose(
            shot, pose_id=_POSE_ID, pose_view=_POSE_VIEW, flipped=False, control_strength=1.0
        )
        snap = applied["pose_provenance"]
        if shared_pose_sha is None:
            shared_pose_sha = snap["pose_asset_sha256"]
        else:
            assert snap["pose_asset_sha256"] == shared_pose_sha
        pose_uri = applied["render_spec"]["pose_asset_uri"]
        pos = _swap_outfit(_load_adopted("C01"), garment)
        if label == "B":
            assert "a3_outfit_b_marker" in pos
            assert "royal blue and white dress" not in pos
        _, png, meta = render_and_gate(
            shot,
            seed=_SEEDS["P05"],
            use_pose=True,
            pose_uri=str(pose_uri),
            positive=pos,
            negative=_DEFAULT_NEG,
        )
        assert meta["pose_prov"].get("pose_asset_sha256") == shared_pose_sha
        if label == "B":
            assert "a3_outfit_b_marker" in meta["final_positive"]
        man = {
            "case": "P05",
            "subcase": f"outfit_{label}",
            "title": "Outfit isolation",
            "character": "C01",
            "seed": _SEEDS["P05"],
            "outfit": label,
            "garment_description": garment,
            "shared_pose_asset_sha256": shared_pose_sha,
            "capability": meta["capability"],
            "sha256": meta["sha256"],
            "width": meta["width"],
            "height": meta["height"],
            "comfy_version": comfy_version,
            "commit": commit,
            "final_positive_prompt": meta["final_positive"],
            "pose_provenance": meta["pose_prov"],
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }
        _write_case(
            f"P05_outfit_{label}",
            png=png,
            manifest=man,
            checklist=[
                f"# P05 Outfit isolation — Outfit {label}",
                "",
                "- [ ] Pose matches sibling (hand-on-hip lean)",
                "- [ ] Outfit differs from the other subcase; character remains Lize",
                "- [x] Auto: shared pose_asset_sha256; outfit tokens differ in prompt",
                "",
                "Notes: _human_",
                "",
            ],
        )
        sheet_rows.append(
            {"png": png, "label": f"P05 outfit{label} s{_SEEDS['P05']}"}
        )
    case_rows.append({"id": "P05", "status": "auto_pass", "sha": "see P05_*"})

    _contact_sheet(sheet_rows)

    summary = [
        "# A3 — Pose Gallery Live (P01–P05)",
        "",
        f"- status_auto: `PASS`",
        f"- status_human: `PENDING`",
        f"- commit: `{commit}`",
        f"- comfy: `{comfy_version}`",
        f"- pose: `{_POSE_ID}` / `{_POSE_VIEW}`",
        f"- recorded_at: `{datetime.now(timezone.utc).isoformat()}`",
        f"- entry: `pnpm test:pose-gallery:live`",
        "",
        "## Cases",
        "",
        "| Case | Seed | Auto | Notes |",
        "|------|------|------|-------|",
        f"| P01 Prompt Pose | {_SEEDS['P01']} | PASS | BaseRender + pose_prompt |",
        f"| P02 Reference / LLLite | {_SEEDS['P02']} | PASS | PoseControlledRender |",
        f"| P03 Flip | {_SEEDS['P03']} | PASS | flipped sha ≠ P02 |",
        f"| P04 Character isolation | {_SEEDS['P04']} | PASS | C01 / C07 / C10 shared pose |",
        f"| P05 Outfit isolation | {_SEEDS['P05']} | PASS | Outfit A/B shared pose |",
        "",
        "## Human review (required for formal A3 PASS)",
        "",
        "- [ ] P01 pose cues readable from prompt-only path",
        "- [ ] P02 posture tracks reference",
        "- [ ] P03 mirrored vs P02",
        "- [ ] **P04** no pose-thumbnail identity leak across C01/C07/C10",
        "- [ ] P05 pose fixed while outfit changes",
        "",
        "Focus: **P04**. Gallery-first fails if reference person identity leaks.",
        "",
        "## Next",
        "",
        "- Human GT on `contact_sheet.png` + per-case checklists",
        "- Then A4 Gate 3 Outfit A→B→C→A",
        "",
    ]
    (_ARTIFACT_DIR / "SUMMARY.md").write_text("\n".join(summary), encoding="utf-8")
    assert len(case_rows) == 5
