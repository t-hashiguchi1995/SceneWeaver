"""A3 rematch r3 — P03 control-image flip evidence + P05 identity/outfit hygiene.

Entry: ``pnpm test:pose-gallery:live:r3``

Focus:
- Persist final LLLite control PNGs for P02/P03 and assert pixel flip
- Record output laterality metrics (not a formal Human PASS)
- Crown lives on Outfit A only; strip from identity; no test markers in prompts
- Rematch P01 / P02+P03 pair / P05; keep P04 tiles
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
from PIL import Image, ImageChops, ImageDraw, ImageFont

from creator_studio.application.studio.scratch import ScratchStudioService
from creator_studio.domain.ids import CharacterId
from creator_studio.domain.wardrobe import OutfitProfile
from creator_studio.infrastructure.container import Container, reset_container
from creator_studio.infrastructure.db.migrate import upgrade_head
from creator_studio.infrastructure.db.session import reset_engine
from creator_studio.infrastructure.settings import Settings, clear_settings_cache
from creator_studio.infrastructure.settings.config import REPO_ROOT
from tests.live.anima_character_semantics import GATE27_PRIMARY
from tests.live.anima_pose_gallery_prompts import (
    OUTFIT_A,
    OUTFIT_B,
    OUTFIT_B_MANIFEST_MARKER,
    assert_no_test_markers,
    prompt_p01_hand_on_head,
    prompt_ref_locked,
)
from tests.live.test_moss_sft_live import _assert_image_gate

pytestmark = pytest.mark.skipif(
    os.environ.get("SCENEWEAVER_POSE_GALLERY_R3", "").lower() not in {"1", "true", "yes"},
    reason="Set SCENEWEAVER_POSE_GALLERY_R3=1 or run: pnpm test:pose-gallery:live:r3",
)

_ARTIFACT_DIR = REPO_ROOT / "docs" / "validation" / "pose-gallery-live"
_ADOPTED = REPO_ROOT / "docs" / "validation" / "anima-gate2_7" / "adopted_prompts"
_SHISEI = REPO_ROOT / "data" / "reference" / "poses" / "shisei"
_REQUIRED_CKPT = "anima_baseV10.safetensors"
_REQUIRED_LLLITE = "anima-lllite-pose-1.safetensors"
_POSE_ID = "sw-pose-0005"
_POSE_VIEW = "diag"
_STRENGTH = 2.0
_SEED_P01 = 33301
_SEED_P02_P03 = 33102
_SEED_P05 = 33105

_NEG = (
    "worst quality, low quality, score_1, score_2, score_3, blurry, jpeg artifacts, "
    "sepia, bad anatomy, bad hands, text, error, missing fingers, extra digit, "
    "fewer digits, cropped, signature, watermark, username, artist name, "
    "standing, walking, running, floating, upper body only, close-up, portrait crop, "
    "hand on knee, hand on cheek, hand near face covering mouth"
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


def _load_adopted() -> str:
    return (_ADOPTED / "C01_lize.anima.txt").read_text(encoding="utf-8").strip()


def _sem(fid: str) -> dict[str, Any]:
    return next(s for s in GATE27_PRIMARY if s["fixture_id"] == fid)


def _lower_left_mass_ratio(png: bytes) -> float:
    """Non-white mass in left half of lower 55% — crude laterality signal."""
    img = Image.open(io.BytesIO(png)).convert("L")
    w, h = img.size
    y0 = int(h * 0.45)
    left = img.crop((0, y0, w // 2, h))
    right = img.crop((w // 2, y0, w, h))

    def mass(im: Image.Image) -> float:
        hist = im.histogram()
        return float(sum(hist[:240])) / float(im.width * im.height)

    lm, rm = mass(left), mass(right)
    total = lm + rm
    return lm / total if total > 1e-6 else 0.5


def _assert_control_flip(ctrl_a: bytes, ctrl_b: bytes) -> dict[str, Any]:
    a = Image.open(io.BytesIO(ctrl_a)).convert("RGB")
    b = Image.open(io.BytesIO(ctrl_b)).convert("RGB")
    assert a.size == b.size
    mirrored = a.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    diff = ImageChops.difference(mirrored, b)
    extrema = diff.getextrema()
    max_delta = max(ch[1] for ch in extrema)
    assert max_delta <= 2, f"control B is not H-flip of A (max_delta={max_delta})"
    return {"max_channel_delta": max_delta, "size": list(a.size)}


@pytest.fixture()
def live_container(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Container, str]:
    runtime = tmp_path / "runtime-pose-gallery-a3-r3"
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


def _seed_char(c: Container, outfit_desc: str, title: str) -> tuple[str, str]:
    sem = _sem("C01")
    char = c.create_character().execute(f"{sem['display_name']} A3r3")
    tags = [t for t in sem["identity_tags"] if "crown" not in t.lower()]
    c.update_visual_identity().execute(
        char.id,
        {
            "identity_tags": tags,
            "character_name": sem["character_name"],
            "franchise": sem["franchise"],
        },
    )
    outfit = OutfitProfile.create(
        title,
        character_id=CharacterId(char.id),
        semantic={"garment_description": outfit_desc},
    )
    with c.uow() as uow:
        uow.outfit_profiles.add(outfit)
        uow.commit()
    return char.id, outfit.id


def _preserve(case_dir: Path) -> None:
    prev = case_dir / "image.png"
    if prev.is_file():
        (case_dir / "image_pre_remediation_r3.png").write_bytes(prev.read_bytes())


def _write_case(case_id: str, png: bytes, manifest: dict[str, Any], checklist: list[str]) -> None:
    d = _ARTIFACT_DIR / case_id
    d.mkdir(parents=True, exist_ok=True)
    _preserve(d)
    (d / "image.png").write_bytes(png)
    (d / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (d / "gt_checklist.md").write_text("\n".join(checklist) + "\n", encoding="utf-8")


def _png_bytes(im: Image.Image) -> bytes:
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return buf.getvalue()


def _contact_sheet(rows: list[dict[str, Any]]) -> None:
    thumb, pad, label_h, cols = 210, 8, 36, 3
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
        (_ARTIFACT_DIR / "contact_sheet_pre_remediation_r3.png").write_bytes(out.read_bytes())
    sheet.save(out, format="PNG")


def _read_pose_control_bytes(c: Container, pose_uri: str) -> bytes:
    path = c.asset_store.path_for_uri(pose_uri)
    data = path.read_bytes()
    img = Image.open(io.BytesIO(data)).convert("RGB")
    return _png_bytes(img)


def test_pose_gallery_a3_remediation_r3(live_container: tuple[Container, str]) -> None:
    c, comfy_version = live_container
    commit = _git_commit()
    studio = ScratchStudioService(c)
    pipe = c.shot_pipeline()
    drafts = c.prompt_draft_service()
    _ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    adopted = _load_adopted()

    ref = Image.open(_SHISEI / _POSE_ID / f"{_POSE_VIEW}.webp").convert("RGB")
    sheet: list[dict[str, Any]] = [
        {"png": _png_bytes(ref), "label": f"REF {_POSE_ID}/{_POSE_VIEW}"},
        {
            "png": _png_bytes(ref.transpose(Image.Transpose.FLIP_LEFT_RIGHT)),
            "label": f"REF flip {_POSE_ID}/{_POSE_VIEW}",
        },
    ]

    def render(
        shot_id: str,
        *,
        seed: int,
        use_pose: bool,
        pose_uri: str | None,
        positive: str,
    ) -> tuple[bytes, dict[str, Any]]:
        assert_no_test_markers(positive)
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
        final = str(attempt.payload.get("final_positive_prompt") or positive)
        assert_no_test_markers(final)
        snap = attempt.payload.get("render_snapshot") or {}
        slots = snap.get("slots") or {}
        return data, {
            "sha256": a.sha256,
            "width": w,
            "height": h,
            "mean_luma": mean,
            "final_positive": final,
            "pose_prov": attempt.payload.get("pose_provenance") or {},
            "capability": attempt.payload.get("capability") or snap.get("capability"),
            "model_id": attempt.payload.get("model_id") or snap.get("model_id"),
            "workflow": attempt.payload.get("workflow_template_id")
            or snap.get("workflow_template_id"),
            "slots_pose": slots.get("pose_image"),
            "slots_strength": slots.get("control_strength"),
        }

    # ---- P01 ----
    print("\n=== R3 P01 ===", flush=True)
    char, outfit = _seed_char(c, OUTFIT_A, "Lize P01 r3")
    shot = studio.create_session(character_id=char, outfit_profile_id=outfit)["shot_id"]
    studio.apply_pose(shot, pose_id=_POSE_ID, pose_view=_POSE_VIEW, pose_method="prompt")
    pos = prompt_p01_hand_on_head(adopted)
    png, meta = render(shot, seed=_SEED_P01, use_pose=False, pose_uri=None, positive=pos)
    assert "hand on top of head" in meta["final_positive"].lower()
    _write_case(
        "P01",
        png,
        {
            "case": "P01",
            "variant": "remediation_r3",
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
            "# P01 r3",
            "- [ ] Seated + knee up + hand on top of head",
            "- [x] Auto: prompt has hand-on-head; no test markers",
            "",
        ],
    )
    sheet.append({"png": png, "label": f"P01 r3 s{_SEED_P01}"})

    shared = prompt_ref_locked(adopted, OUTFIT_A)
    assert "silver crown" in shared
    assert OUTFIT_B_MANIFEST_MARKER not in shared

    # ---- P02 ----
    print("\n=== R3 P02 (+ control evidence) ===", flush=True)
    char, outfit = _seed_char(c, OUTFIT_A, "Lize P02 r3")
    shot = studio.create_session(character_id=char, outfit_profile_id=outfit)["shot_id"]
    applied = studio.apply_pose(
        shot,
        pose_id=_POSE_ID,
        pose_view=_POSE_VIEW,
        flipped=False,
        control_strength=_STRENGTH,
    )
    pose_uri = str(applied["render_spec"]["pose_asset_uri"])
    ctrl_p02 = _read_pose_control_bytes(c, pose_uri)
    p02_ctrl_sha = hashlib.sha256(ctrl_p02).hexdigest()
    (_ARTIFACT_DIR / "P02").mkdir(parents=True, exist_ok=True)
    (_ARTIFACT_DIR / "P02" / "control.png").write_bytes(ctrl_p02)
    png_p02, meta = render(
        shot, seed=_SEED_P02_P03, use_pose=True, pose_uri=pose_uri, positive=shared
    )
    assert float(meta["slots_strength"] or 0) == _STRENGTH
    assert meta["slots_pose"] == pose_uri
    lat_p02 = _lower_left_mass_ratio(png_p02)
    _write_case(
        "P02",
        png_p02,
        {
            "case": "P02",
            "variant": "remediation_r3",
            "seed": _SEED_P02_P03,
            "pose_id": _POSE_ID,
            "pose_view": _POSE_VIEW,
            "flipped": False,
            "control_strength": _STRENGTH,
            "control_png_sha256": p02_ctrl_sha,
            "output_laterality_left_mass_ratio": round(lat_p02, 4),
            "capability": meta["capability"],
            "sha256": meta["sha256"],
            "width": meta["width"],
            "height": meta["height"],
            "comfy_version": comfy_version,
            "commit": commit,
            "final_positive_prompt": meta["final_positive"],
            "pose_provenance": meta["pose_prov"],
            "slots_pose_image": meta["slots_pose"],
            "slots_control_strength": meta["slots_strength"],
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        },
        [
            "# P02 r3",
            "- [ ] Seated REF cues (knee up, hand on head)",
            f"- [x] Auto: strength {_STRENGTH}; control.png saved; slots.pose_image set",
            "",
        ],
    )
    sheet.append({"png": ctrl_p02, "label": "CTRL P02 unflipped"})
    sheet.append({"png": png_p02, "label": f"P02 r3 s{_SEED_P02_P03}"})

    # ---- P03 ----
    print("\n=== R3 P03 flip (+ control flip assert) ===", flush=True)
    char, outfit = _seed_char(c, OUTFIT_A, "Lize P03 r3")
    shot = studio.create_session(character_id=char, outfit_profile_id=outfit)["shot_id"]
    applied = studio.apply_pose(
        shot,
        pose_id=_POSE_ID,
        pose_view=_POSE_VIEW,
        flipped=True,
        control_strength=_STRENGTH,
    )
    pose_uri = str(applied["render_spec"]["pose_asset_uri"])
    ctrl_p03 = _read_pose_control_bytes(c, pose_uri)
    flip_stats = _assert_control_flip(ctrl_p02, ctrl_p03)
    (_ARTIFACT_DIR / "P03").mkdir(parents=True, exist_ok=True)
    (_ARTIFACT_DIR / "P03" / "control.png").write_bytes(ctrl_p03)
    png_p03, meta = render(
        shot, seed=_SEED_P02_P03, use_pose=True, pose_uri=pose_uri, positive=shared
    )
    assert meta["final_positive"] == shared
    assert meta["pose_prov"].get("flipped") is True
    lat_p03 = _lower_left_mass_ratio(png_p03)
    _write_case(
        "P03",
        png_p03,
        {
            "case": "P03",
            "variant": "remediation_r3",
            "seed": _SEED_P02_P03,
            "paired_with": "P02",
            "pose_id": _POSE_ID,
            "pose_view": _POSE_VIEW,
            "flipped": True,
            "control_strength": _STRENGTH,
            "same_prompt_as_p02": True,
            "control_png_sha256": hashlib.sha256(ctrl_p03).hexdigest(),
            "control_flip_check": flip_stats,
            "output_laterality_left_mass_ratio": round(lat_p03, 4),
            "output_laterality_delta_vs_p02": round(lat_p03 - lat_p02, 4),
            "capability": meta["capability"],
            "sha256": meta["sha256"],
            "width": meta["width"],
            "height": meta["height"],
            "comfy_version": comfy_version,
            "commit": commit,
            "final_positive_prompt": meta["final_positive"],
            "pose_provenance": meta["pose_prov"],
            "slots_pose_image": meta["slots_pose"],
            "slots_control_strength": meta["slots_strength"],
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        },
        [
            "# P03 r3",
            "- [ ] Output mirror of P02 (knee / head-arm laterality)",
            "- [x] Auto: control.png is pixel H-flip of P02 control; same seed+prompt",
            f"- laterality left-mass P02={lat_p02:.3f} P03={lat_p03:.3f} "
            f"(delta={lat_p03 - lat_p02:.3f}; heuristic only)",
            "",
        ],
    )
    sheet.append({"png": ctrl_p03, "label": "CTRL P03 flipped"})
    sheet.append({"png": png_p03, "label": f"P03 r3 flip s{_SEED_P02_P03}"})

    for fid in ("C01", "C07", "C10"):
        p = _ARTIFACT_DIR / f"P04_{fid}" / "image.png"
        if p.is_file():
            sheet.append({"png": p.read_bytes(), "label": f"P04 {fid} (kept)"})

    # ---- P05 ----
    print("\n=== R3 P05 outfit hygiene + pose lock ===", flush=True)
    char, outfit_a = _seed_char(c, OUTFIT_A, "Lize P05A r3")
    outfit_b = OutfitProfile.create(
        "Lize P05B r3",
        character_id=CharacterId(char),
        semantic={"garment_description": OUTFIT_B},
    )
    with c.uow() as uow:
        uow.outfit_profiles.add(outfit_b)
        uow.commit()

    shared_pose_sha: str | None = None
    for label, oid, garment in (("A", outfit_a, OUTFIT_A), ("B", outfit_b.id, OUTFIT_B)):
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
        pos = prompt_ref_locked(adopted, garment)
        if label == "A":
            assert "silver crown" in pos
        else:
            assert "silver crown" not in pos
            assert OUTFIT_B_MANIFEST_MARKER not in pos
        png, meta = render(
            shot,
            seed=_SEED_P05,
            use_pose=True,
            pose_uri=str(applied["render_spec"]["pose_asset_uri"]),
            positive=pos,
        )
        has_silver_crown = "silver crown" in meta["final_positive"].lower()
        man = {
            "case": "P05",
            "variant": "remediation_r3",
            "subcase": f"outfit_{label}",
            "seed": _SEED_P05,
            "outfit": label,
            "control_strength": _STRENGTH,
            "shared_pose_asset_sha256": shared_pose_sha,
            "manifest_marker": OUTFIT_B_MANIFEST_MARKER if label == "B" else None,
            "marker_in_prompt": False,
            "silver_crown_in_prompt": has_silver_crown,
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
        if label == "A":
            assert has_silver_crown
        else:
            assert not has_silver_crown
        _write_case(
            f"P05_outfit_{label}",
            png,
            man,
            [
                f"# P05 r3 outfit {label}",
                "- [ ] Same seated posture/framing as sibling",
                "- [ ] Outfit differs; Lize identity",
                f"- [x] Auto: strength {_STRENGTH}; no test marker in prompt; "
                f"silver_crown={'yes' if label == 'A' else 'no'}",
                "",
            ],
        )
        sheet.append({"png": png, "label": f"P05 {label} r3 s{_SEED_P05}"})

    _contact_sheet(sheet)

    summary_path = _ARTIFACT_DIR / "SUMMARY.md"
    prior = summary_path.read_text(encoding="utf-8") if summary_path.is_file() else ""
    block = f"""
## Remediation r3 rematch

- status_auto: `PASS` (r3 rematch generated)
- status_human: `PENDING`
- commit: `{commit}`
- comfy: `{comfy_version}`
- control_strength: `{_STRENGTH}`
- P02/P03 seed: `{_SEED_P02_P03}` (identical prompt; flip only)
- P01 seed: `{_SEED_P01}`
- P05 seed: `{_SEED_P05}`
- recorded_at: `{datetime.now(timezone.utc).isoformat()}`
- entry: `pnpm test:pose-gallery:live:r3`

### Auto evidence upgrades

1. `P02/control.png` and `P03/control.png` are the final bytes fed as `pose_image`
2. Pixel assert: P03 control == H-flip(P02 control)
3. Output laterality heuristic recorded in manifests (not Human PASS)
4. Crown is Outfit A only; `a3_outfit_b_marker` lives in manifest, never in prompt

### Human recheck focus

1. P03 vs P02 body laterality (use CTRL tiles + outputs)
2. P05 A vs B joint/camera lock with crown absent on B
3. P01 hand-on-head
4. P02 still tracks REF after strength 2.0

Prior: `HUMAN_REVIEW_20261102.md`, `HUMAN_REMATCH_REVIEW_20261102.md`
"""
    if "## Remediation r3 rematch" in prior:
        head = prior.split("## Remediation r3 rematch")[0].rstrip()
        summary_path.write_text(head + "\n" + block, encoding="utf-8")
    else:
        summary_path.write_text(prior.rstrip() + "\n" + block, encoding="utf-8")
