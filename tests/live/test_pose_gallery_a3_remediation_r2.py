"""A3 rematch r2 — fix P01 hand-on-head, P03 output flip, P05 pose lock.

Entry: ``pnpm test:pose-gallery:live:r2``

Keeps P04 images. Regenerates P01, P02+P03 (paired; control method change), P05 A/B.

Key fix for P03: strip limb-laterality text from the shared prompt so LLLite
(not identical pose tags) drives left/right; raise control_strength.
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
    os.environ.get("SCENEWEAVER_POSE_GALLERY_R2", "").lower() not in {"1", "true", "yes"},
    reason="Set SCENEWEAVER_POSE_GALLERY_R2=1 or run: pnpm test:pose-gallery:live:r2",
)

_ARTIFACT_DIR = REPO_ROOT / "docs" / "validation" / "pose-gallery-live"
_ADOPTED = REPO_ROOT / "docs" / "validation" / "anima-gate2_7" / "adopted_prompts"
_SHISEI = REPO_ROOT / "data" / "reference" / "poses" / "shisei"
_REQUIRED_CKPT = "anima_baseV10.safetensors"
_REQUIRED_LLLITE = "anima-lllite-pose-1.safetensors"
_POSE_ID = "sw-pose-0005"
_POSE_VIEW = "diag"
_STRENGTH = 1.85
_SEED_P01 = 33201
_SEED_P02_P03 = 33102  # keep paired seed from prior rematch
_SEED_P05 = 33105
_SKIP_P01 = os.environ.get("SCENEWEAVER_POSE_GALLERY_R2_SKIP_P01", "").lower() in {
    "1",
    "true",
    "yes",
}

_NEG = (
    "worst quality, low quality, score_1, score_2, score_3, blurry, jpeg artifacts, "
    "sepia, bad anatomy, bad hands, text, error, missing fingers, extra digit, "
    "fewer digits, cropped, signature, watermark, username, artist name, "
    "standing, walking, running, floating, upper body only, close-up, portrait crop, "
    "hand on knee, hand on cheek, hand near face covering mouth"
)

_FRAME = "full body, entire body visible, from head to toe, wide shot, feet visible"
_OUTFIT_A = "royal blue and white dress, blue jacket, white blouse"
_OUTFIT_B = "red cardigan, white blouse, plaid skirt, loafers, school uniform, a3_outfit_b_marker"


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
        pytest.fail(f"ENV: ComfyUI unreachable: {exc}")
    system = stats.get("system") if isinstance(stats, dict) else {}
    version = str((system or {}).get("comfyui_version") or "")
    ckpts = [str(x).replace("\\", "/") for x in (_comfy_get(comfy_url, "/models/checkpoints") or [])]
    if not any(_REQUIRED_CKPT in p for p in ckpts):
        pytest.fail(f"ENV: missing {_REQUIRED_CKPT}")
    patches = [str(x).replace("\\", "/") for x in (_comfy_get(comfy_url, "/models/model_patches") or [])]
    if not any(_REQUIRED_LLLITE in p for p in patches):
        pytest.fail(f"ENV: missing {_REQUIRED_LLLITE}")
    info = _comfy_get(comfy_url, "/object_info/AnimaLLLiteApply")
    if not isinstance(info, dict) or "AnimaLLLiteApply" not in info:
        pytest.fail("ENV: AnimaLLLiteApply missing")
    return version or "unknown"


def _load_adopted(fid: str) -> str:
    name = {"C01": "C01_lize.anima.txt"}[fid]
    return (_ADOPTED / name).read_text(encoding="utf-8").strip()


def _sem(fid: str) -> dict[str, Any]:
    return next(s for s in GATE27_PRIMARY if s["fixture_id"] == fid)


def _identity_core(adopted: str) -> str:
    """Strip pose/camera/outfit to identity + expression stubs for rebuild."""
    # Keep through feather ornament; drop dress onward for controlled rebuild
    marker = ", royal blue and white dress"
    if marker in adopted:
        return adopted.split(marker)[0]
    return adopted


def _prompt_p01(adopted: str) -> str:
    core = _identity_core(adopted)
    return (
        f"{core}, {_OUTFIT_A}, silver crown, calm expression, "
        f"sitting on ground, one knee raised, "
        f"one hand on top of head, palm flat on crown of head, arm raised above head, "
        f"other forearm resting on raised knee, opposite leg extended, "
        f"asymmetric pose, {_FRAME}, eye level, simple studio background, soft lighting"
    )


def _prompt_ref_locked(adopted: str, outfit: str, *, keep_crown: bool) -> str:
    """Shared locked pose text for P02/P03/P05 (identical across flip pair).

    Limb cues are side-agnostic (no left/right) so a flipped reference can still
    own laterality, while remaining specific enough for knee-up + hand-on-head.
    """
    core = _identity_core(adopted)
    if not keep_crown:
        parts = [
            p.strip()
            for p in core.split(",")
            if p.strip() and "crown" not in p.strip().lower()
        ]
        core = ", ".join(parts)
    crown = ", silver crown" if keep_crown else ""
    return (
        f"{core}, {outfit}{crown}, calm expression, "
        f"sitting on ground, one knee raised toward chest, "
        f"one hand on top of head, palm on crown of head, arm raised above head, "
        f"other forearm resting on raised knee, opposite leg extended along ground, "
        f"asymmetric seated pose, pose follows reference, {_FRAME}, "
        f"eye level, simple studio background, soft lighting"
    )


@pytest.fixture()
def live_container(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Container, str]:
    runtime = tmp_path / "runtime-pose-gallery-a3-r2"
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


def _seed_char(c: Container, fid: str, outfit_desc: str, title: str) -> tuple[str, str]:
    sem = _sem(fid)
    char = c.create_character().execute(f"{sem['display_name']} A3r2")
    c.update_visual_identity().execute(
        char.id,
        {
            "identity_tags": list(sem["identity_tags"]),
            "character_name": sem["character_name"],
            "franchise": sem["franchise"],
        },
    )
    outfit = OutfitProfile.create(
        title, character_id=CharacterId(char.id), semantic={"garment_description": outfit_desc}
    )
    with c.uow() as uow:
        uow.outfit_profiles.add(outfit)
        uow.commit()
    return char.id, outfit.id


def _preserve(case_dir: Path) -> None:
    prev = case_dir / "image.png"
    if prev.is_file():
        (case_dir / "image_pre_remediation_r2.png").write_bytes(prev.read_bytes())


def _write_case(case_id: str, png: bytes, manifest: dict[str, Any], checklist: list[str]) -> None:
    d = _ARTIFACT_DIR / case_id
    d.mkdir(parents=True, exist_ok=True)
    _preserve(d)
    (d / "image.png").write_bytes(png)
    (d / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (d / "gt_checklist.md").write_text("\n".join(checklist) + "\n", encoding="utf-8")


def _contact_sheet(rows: list[dict[str, Any]]) -> None:
    thumb, pad, label_h, cols = 220, 8, 38, 3
    n = len(rows)
    rows_n = (n + cols - 1) // cols
    cell_w, cell_h = thumb, thumb + label_h
    sheet = Image.new(
        "RGB",
        (cols * cell_w + (cols + 1) * pad, rows_n * cell_h + (rows_n + 1) * pad),
        (18, 18, 22),
    )
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 10)
    except OSError:
        font = ImageFont.load_default()
    for i, row in enumerate(rows):
        r, c = divmod(i, cols)
        x0 = pad + c * (cell_w + pad)
        y0 = pad + r * (cell_h + pad)
        img = Image.open(io.BytesIO(row["png"])).convert("RGB")
        img.thumbnail((thumb, thumb))
        sheet.paste(img, (x0 + (thumb - img.width) // 2, y0 + (thumb - img.height) // 2))
        draw.text((x0 + 4, y0 + thumb + 4), row["label"][:40], fill=(230, 230, 235), font=font)
    out = _ARTIFACT_DIR / "contact_sheet.png"
    if out.is_file():
        (_ARTIFACT_DIR / "contact_sheet_pre_remediation_r2.png").write_bytes(out.read_bytes())
    sheet.save(out, format="PNG")


def test_pose_gallery_a3_remediation_r2(live_container: tuple[Container, str]) -> None:
    c, comfy_version = live_container
    commit = _git_commit()
    studio = ScratchStudioService(c)
    pipe = c.shot_pipeline()
    drafts = c.prompt_draft_service()
    _ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    detail = c.reference_pose_service().get_detail(_POSE_ID)
    assert detail is not None
    pose_prompt = str(((detail.get("views") or {}).get(_POSE_VIEW) or {}).get("prompt") or "")
    assert "sitting" in pose_prompt.lower()

    ref = Image.open(_SHISEI / _POSE_ID / f"{_POSE_VIEW}.webp").convert("RGB")
    ref_flip = ref.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    def _png(im: Image.Image) -> bytes:
        b = io.BytesIO()
        im.save(b, format="PNG")
        return b.getvalue()

    sheet: list[dict[str, Any]] = [
        {"png": _png(ref), "label": f"REF {_POSE_ID}/{_POSE_VIEW}"},
        {"png": _png(ref_flip), "label": f"REF flip {_POSE_ID}/{_POSE_VIEW}"},
    ]

    def render(
        shot_id: str,
        *,
        seed: int,
        use_pose: bool,
        pose_uri: str | None,
        positive: str,
    ) -> tuple[bytes, dict[str, Any]]:
        drafts.update_edits(shot_id, positive, _NEG)
        pipe.update_shot(shot_id, {"camera": {"shot": "full body", "angle": "eye level"}})
        result = pipe.render(shot_id, use_pose=use_pose, pose_asset_uri=pose_uri, seed=seed)
        studio.mark_generated(shot_id)
        attempt = pipe.get_attempt(result["generation_attempt_id"])
        assert attempt.seed == seed
        asset_id = result["output_asset_ids"][0]
        with c.uow() as uow:
            a = uow.assets.get(asset_id)
            assert a is not None
            data = c.asset_store.path_for_uri(a.uri).read_bytes()
            assert hashlib.sha256(data).hexdigest() == a.sha256
        w, h, mean = _assert_image_gate(data)
        return data, {
            "sha256": a.sha256,
            "width": w,
            "height": h,
            "mean_luma": mean,
            "final_positive": attempt.payload.get("final_positive_prompt") or positive,
            "pose_prov": attempt.payload.get("pose_provenance") or {},
            "capability": attempt.payload.get("capability")
            or (attempt.payload.get("render_snapshot") or {}).get("capability"),
            "model_id": attempt.payload.get("model_id")
            or (attempt.payload.get("render_snapshot") or {}).get("model_id"),
            "workflow": attempt.payload.get("workflow_template_id")
            or (attempt.payload.get("render_snapshot") or {}).get("workflow_template_id"),
        }

    adopted = _load_adopted("C01")

    # ---- P01 ----
    if _SKIP_P01 and (_ARTIFACT_DIR / "P01" / "image.png").is_file():
        print("\n=== R2 P01 skipped (keep prior r2 image) ===", flush=True)
        sheet.append(
            {
                "png": (_ARTIFACT_DIR / "P01" / "image.png").read_bytes(),
                "label": f"P01 r2 kept s{_SEED_P01}",
            }
        )
    else:
        print("\n=== R2 P01 hand-on-head ===", flush=True)
        char, outfit = _seed_char(c, "C01", _OUTFIT_A, "Lize P01")
        shot = studio.create_session(character_id=char, outfit_profile_id=outfit)["shot_id"]
        studio.apply_pose(shot, pose_id=_POSE_ID, pose_view=_POSE_VIEW, pose_method="prompt")
        pos = _prompt_p01(adopted)
        assert "palm flat on crown" in pos or "hand on top of head" in pos
        png, meta = render(shot, seed=_SEED_P01, use_pose=False, pose_uri=None, positive=pos)
        assert meta["capability"] == "BaseRender"
        assert "hand on top of head" in meta["final_positive"].lower()
        _write_case(
            "P01",
            png,
            {
                "case": "P01",
                "variant": "remediation_r2",
                "seed": _SEED_P01,
                "pose_id": _POSE_ID,
                "pose_view": _POSE_VIEW,
                "pose_method": "prompt",
                "capability": meta["capability"],
                "sha256": meta["sha256"],
                "width": meta["width"],
                "height": meta["height"],
                "comfy_version": comfy_version,
                "commit": commit,
                "final_positive_prompt": meta["final_positive"],
                "pose_provenance": meta["pose_prov"],
                "recorded_at": datetime.now(timezone.utc).isoformat(),
            },
            [
                "# P01 r2",
                "- [ ] Seated + one knee up + **hand on top of head**",
                "- [ ] Full body",
                "- [x] Auto: prompt includes palm/hand on head; BaseRender",
                "",
            ],
        )
        sheet.append({"png": png, "label": f"P01 r2 s{_SEED_P01}"})

    # Shared locked pose prompt for P02/P03 (identical; no left/right words)
    shared_ref_prompt = _prompt_ref_locked(adopted, _OUTFIT_A, keep_crown=True)
    assert "left" not in shared_ref_prompt.lower()
    assert "right" not in shared_ref_prompt.lower()
    assert "hand on top of head" in shared_ref_prompt.lower()
    assert "one knee raised" in shared_ref_prompt.lower()

    # ---- P02 (regression pair for strength/prompt change) ----
    print("\n=== R2 P02 reference (paired) ===", flush=True)
    char, outfit = _seed_char(c, "C01", _OUTFIT_A, "Lize P02r2")
    shot = studio.create_session(character_id=char, outfit_profile_id=outfit)["shot_id"]
    applied = studio.apply_pose(
        shot,
        pose_id=_POSE_ID,
        pose_view=_POSE_VIEW,
        flipped=False,
        control_strength=_STRENGTH,
    )
    assert applied["pose_provenance"]["pose_method"] == "reference_image"
    p02_sha = applied["pose_provenance"]["pose_asset_sha256"]
    pose_uri = applied["render_spec"]["pose_asset_uri"]
    png_p02, meta = render(
        shot, seed=_SEED_P02_P03, use_pose=True, pose_uri=str(pose_uri), positive=shared_ref_prompt
    )
    assert meta["capability"] == "PoseControlledRender"
    assert float(meta["pose_prov"].get("control_strength") or 0) == _STRENGTH
    _write_case(
        "P02",
        png_p02,
        {
            "case": "P02",
            "variant": "remediation_r2",
            "seed": _SEED_P02_P03,
            "pose_id": _POSE_ID,
            "pose_view": _POSE_VIEW,
            "flipped": False,
            "control_strength": _STRENGTH,
            "prompt_mode": "side_agnostic_locked",
            "capability": meta["capability"],
            "sha256": meta["sha256"],
            "width": meta["width"],
            "height": meta["height"],
            "comfy_version": comfy_version,
            "commit": commit,
            "final_positive_prompt": meta["final_positive"],
            "pose_provenance": meta["pose_prov"],
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        },
        [
            "# P02 r2 (paired with P03)",
            "- [ ] Seated REF cues (knee up, hand on head)",
            f"- [x] Auto: strength {_STRENGTH}; side-agnostic locked pose prompt",
            "",
        ],
    )
    sheet.append({"png": png_p02, "label": f"P02 r2 s{_SEED_P02_P03}"})

    # ---- P03 flip ----
    print("\n=== R2 P03 flip (same seed+prompt; flipped ref only) ===", flush=True)
    char, outfit = _seed_char(c, "C01", _OUTFIT_A, "Lize P03r2")
    shot = studio.create_session(character_id=char, outfit_profile_id=outfit)["shot_id"]
    applied = studio.apply_pose(
        shot,
        pose_id=_POSE_ID,
        pose_view=_POSE_VIEW,
        flipped=True,
        control_strength=_STRENGTH,
    )
    snap = applied["pose_provenance"]
    assert snap["flipped"] is True
    assert snap["pose_asset_sha256"] != p02_sha
    pose_uri = applied["render_spec"]["pose_asset_uri"]
    # Exact same positive as P02
    png_p03, meta = render(
        shot, seed=_SEED_P02_P03, use_pose=True, pose_uri=str(pose_uri), positive=shared_ref_prompt
    )
    assert meta["pose_prov"].get("flipped") is True
    assert meta["final_positive"] == shared_ref_prompt
    _write_case(
        "P03",
        png_p03,
        {
            "case": "P03",
            "variant": "remediation_r2",
            "seed": _SEED_P02_P03,
            "paired_with": "P02",
            "pose_id": _POSE_ID,
            "pose_view": _POSE_VIEW,
            "flipped": True,
            "control_strength": _STRENGTH,
            "prompt_mode": "side_agnostic_locked",
            "same_prompt_as_p02": True,
            "pose_asset_sha256": snap["pose_asset_sha256"],
            "unflipped_pose_asset_sha256": p02_sha,
            "capability": meta["capability"],
            "sha256": meta["sha256"],
            "width": meta["width"],
            "height": meta["height"],
            "comfy_version": comfy_version,
            "commit": commit,
            "final_positive_prompt": meta["final_positive"],
            "pose_provenance": meta["pose_prov"],
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        },
        [
            "# P03 r2",
            "- [ ] Output mirror of P02 (raised knee / head-arm laterality)",
            "- [ ] Compare REF flip tile",
            f"- [x] Auto: same seed+prompt; flipped asset sha ≠ P02; strength {_STRENGTH}",
            "",
        ],
    )
    sheet.append({"png": png_p03, "label": f"P03 r2 flip s{_SEED_P02_P03}"})

    # Keep P04 tiles from disk
    for fid in ("C01", "C07", "C10"):
        p = _ARTIFACT_DIR / f"P04_{fid}" / "image.png"
        if p.is_file():
            sheet.append({"png": p.read_bytes(), "label": f"P04 {fid} (kept)"})

    # ---- P05 A/B ----
    print("\n=== R2 P05 outfit lock ===", flush=True)
    char, outfit_a = _seed_char(c, "C01", _OUTFIT_A, "Lize P05A")
    outfit_b = OutfitProfile.create(
        "Lize P05B",
        character_id=CharacterId(char),
        semantic={"garment_description": _OUTFIT_B},
    )
    with c.uow() as uow:
        uow.outfit_profiles.add(outfit_b)
        uow.commit()

    shared_pose_sha: str | None = None
    for label, oid, garment, keep_crown in (
        ("A", outfit_a, _OUTFIT_A, True),
        ("B", outfit_b.id, _OUTFIT_B, False),
    ):
        shot = studio.create_session(character_id=char, outfit_profile_id=oid)["shot_id"]
        applied = studio.apply_pose(
            shot,
            pose_id=_POSE_ID,
            pose_view=_POSE_VIEW,
            flipped=False,
            control_strength=_STRENGTH,
        )
        snap = applied["pose_provenance"]
        if shared_pose_sha is None:
            shared_pose_sha = snap["pose_asset_sha256"]
        else:
            assert snap["pose_asset_sha256"] == shared_pose_sha
        pos = _prompt_ref_locked(adopted, garment, keep_crown=keep_crown)
        png, meta = render(
            shot,
            seed=_SEED_P05,
            use_pose=True,
            pose_uri=str(applied["render_spec"]["pose_asset_uri"]),
            positive=pos,
        )
        if label == "B":
            assert "a3_outfit_b_marker" in meta["final_positive"]
            assert "silver crown" not in meta["final_positive"].lower()
        _write_case(
            f"P05_outfit_{label}",
            png,
            {
                "case": "P05",
                "variant": "remediation_r2",
                "subcase": f"outfit_{label}",
                "seed": _SEED_P05,
                "outfit": label,
                "control_strength": _STRENGTH,
                "prompt_mode": "side_agnostic_locked",
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
            },
            [
                f"# P05 r2 outfit {label}",
                "- [ ] Same seated posture/framing as sibling",
                "- [ ] Outfit differs; Lize identity",
                f"- [x] Auto: strength {_STRENGTH}; locked pose text; same seed+pose sha",
                "",
            ],
        )
        sheet.append({"png": png, "label": f"P05 {label} r2 s{_SEED_P05}"})

    _contact_sheet(sheet)

    # Append rematch r2 block to SUMMARY without erasing prior human FAIL history
    summary_path = _ARTIFACT_DIR / "SUMMARY.md"
    prior = summary_path.read_text(encoding="utf-8") if summary_path.is_file() else ""
    block = f"""
## Remediation r2 rematch

- status_auto: `PASS` (r2 rematch generated)
- status_human: `PENDING`
- commit: `{commit}`
- comfy: `{comfy_version}`
- control_strength: `{_STRENGTH}`
- prompt_mode: side-agnostic locked pose cues (no left/right words) for P02/P03/P05
- P02/P03 seed: `{_SEED_P02_P03}` (identical prompt+seed; flip only)
- P01 seed: `{_SEED_P01}`
- P05 seed: `{_SEED_P05}`
- recorded_at: `{datetime.now(timezone.utc).isoformat()}`
- entry: `pnpm test:pose-gallery:live:r2`

### Hypothesis addressed

1. Prompt limb text with implied side competed with flipped refs → use side-agnostic
   but still specific locked cues + higher LLLite strength.
2. P05 pose drift from weak control / crown+outfit churn → strength {_STRENGTH},
   crown stripped on B, identical pose text.

### Human recheck focus

1. P03 vs P02: mirrored knee / head-arm laterality (not SHA alone)
2. P05 A vs B: joint layout + camera stay fixed
3. P01: hand clearly on top of head
4. P02 regression: still seated with REF cues after strength/prompt change

Prior reviews: `HUMAN_REVIEW_20261102.md`, `HUMAN_REMATCH_REVIEW_20261102.md`
"""
    if "## Remediation r2 rematch" in prior:
        head = prior.split("## Remediation r2 rematch")[0].rstrip()
        summary_path.write_text(head + "\n" + block, encoding="utf-8")
    else:
        summary_path.write_text(prior.rstrip() + "\n" + block, encoding="utf-8")
