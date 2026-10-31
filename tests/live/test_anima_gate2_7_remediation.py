"""Gate 2.7 remediation rematch — C02 / C04 / C06 / C11 at fixed seeds.

Entry: ``pnpm test:anima:gate2_7:remediation``

Does not re-run full C01–C11. Overwrites only remediated fixture folders and
rebuilds contact sheet from existing C* images + new rematches.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import subprocess
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont

from creator_studio.application.projects.create_project import CreateProjectCommand
from creator_studio.domain.prompt import compute_prompt_hash
from creator_studio.infrastructure.container import Container, reset_container
from creator_studio.infrastructure.db.migrate import upgrade_head
from creator_studio.infrastructure.db.session import reset_engine
from creator_studio.infrastructure.settings import Settings, clear_settings_cache
from creator_studio.infrastructure.settings.config import REPO_ROOT
from tests.live.anima_character_semantics import GATE27_PRIMARY, GATE27_SLUGS, to_anima_render_spec
from tests.live.anima_gate2_7_remediation import REMEDIATIONS
from tests.live.test_moss_sft_live import _assert_image_gate

pytestmark = pytest.mark.skipif(
    os.environ.get("SCENEWEAVER_GATE27_REMEDIATION", "").lower() not in {"1", "true", "yes"},
    reason="Set SCENEWEAVER_GATE27_REMEDIATION=1 or run: pnpm test:anima:gate2_7:remediation",
)

_ARTIFACT_DIR = REPO_ROOT / "docs" / "validation" / "anima-gate2_7"
_MIN_EDGE = 512
_REQUIRED_CKPT = "anima_baseV10.safetensors"
_SHEET_THUMB = 280
_SHEET_PAD = 8
_LABEL_H = 36
_COLS = 4
_DEFAULT_NEG = (
    "lowres, bad anatomy, bad hands, text, error, missing fingers, "
    "extra digit, fewer digits, cropped, worst quality, low quality, "
    "normal quality, jpeg artifacts, signature, watermark, username, blurry"
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


def _require_anima_runtime(comfy_url: str) -> str:
    try:
        stats = _comfy_get(comfy_url, "/system_stats")
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        pytest.fail(f"ENV: ComfyUI unreachable at {comfy_url}: {exc}")
    system = stats.get("system") if isinstance(stats, dict) else {}
    version = str((system or {}).get("comfyui_version") or "")
    data = _comfy_get(comfy_url, "/models/checkpoints")
    ckpts = [str(x).replace("\\", "/") for x in (data if isinstance(data, list) else [])]
    if not any(_REQUIRED_CKPT in p for p in ckpts):
        pytest.fail(f"ENV: Anima checkpoint missing ({_REQUIRED_CKPT})")
    return version or "unknown"


@pytest.fixture()
def live_container(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Container, str]:
    runtime = tmp_path / "runtime-anima-gate2_7-remediation"
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
    return Container(settings), _require_anima_runtime(comfy_url)


def _rebuild_contact_sheet() -> None:
    rows: list[dict] = []
    for sem in GATE27_PRIMARY:
        fid = sem["fixture_id"]
        png = _ARTIFACT_DIR / fid / "image.png"
        man = _ARTIFACT_DIR / fid / "manifest.json"
        if not png.is_file():
            continue
        manifest = json.loads(man.read_text(encoding="utf-8")) if man.is_file() else {}
        rows.append(
            {
                "fixture_id": fid,
                "fixture_name": sem["display_name"],
                "seed": manifest.get("seed", ""),
                "png_bytes": png.read_bytes(),
            }
        )
    cols = _COLS
    n = len(rows)
    rows_n = (n + cols - 1) // cols
    cell_w = _SHEET_THUMB
    cell_h = _SHEET_THUMB + _LABEL_H
    sheet_w = cols * cell_w + (cols + 1) * _SHEET_PAD
    sheet_h = rows_n * cell_h + (rows_n + 1) * _SHEET_PAD
    sheet = Image.new("RGB", (sheet_w, sheet_h), (18, 18, 22))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 12)
    except OSError:
        font = ImageFont.load_default()
    for i, row in enumerate(rows):
        r, c = divmod(i, cols)
        x0 = _SHEET_PAD + c * (cell_w + _SHEET_PAD)
        y0 = _SHEET_PAD + r * (cell_h + _SHEET_PAD)
        img = Image.open(io.BytesIO(row["png_bytes"])).convert("RGB")
        img.thumbnail((cell_w, _SHEET_THUMB))
        ox = x0 + (cell_w - img.width) // 2
        oy = y0 + (_SHEET_THUMB - img.height) // 2
        sheet.paste(img, (ox, oy))
        label = f"{row['fixture_id']} {row['fixture_name'][:10]} s{row['seed']}"
        draw.text((x0 + 4, y0 + _SHEET_THUMB + 4), label, fill=(230, 230, 235), font=font)
    out = _ARTIFACT_DIR / "contact_sheet.png"
    sheet.save(out, format="PNG")


def _write_gt_checklist(fid: str, name: str, rem: dict, items: list[tuple[str, str]]) -> None:
    lines = [
        f"# GT checklist — {fid} {name} (remediation)",
        "",
        f"- Seed: `{rem['seed']}` (unchanged)",
        f"- Notes: {rem['notes']}",
        "",
    ]
    for key, status in items:
        mark = "[x]" if status == "pass" else "[ ]"
        lines.append(f"- {mark} {key}")
    lines.extend(["", "Score (0–8): _ (human rematch)", "Notes:", ""])
    (_ARTIFACT_DIR / fid / "gt_checklist.md").write_text("\n".join(lines), encoding="utf-8")


def test_gate2_7_remediation_rematch(live_container: tuple[Container, str]) -> None:
    c, comfy_version = live_container
    commit = _git_commit()
    assert set(REMEDIATIONS) == {"C02", "C04", "C06", "C11"}

    _ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    (_ARTIFACT_DIR / "adopted_prompts").mkdir(parents=True, exist_ok=True)

    project = c.create_project().execute(CreateProjectCommand(title="Anima Gate2.7 Remediation"))
    scene = c.create_scene().execute(project.id, "Studio")
    pipe = c.shot_pipeline()
    drafts = c.prompt_draft_service()
    by_id = {s["fixture_id"]: s for s in GATE27_PRIMARY}

    rematch_rows: list[dict] = []
    for fid, rem in REMEDIATIONS.items():
        sem = by_id[fid]
        slug = GATE27_SLUGS[fid]
        seed = rem["seed"]
        print(f"\n=== REMEDIATE {fid} {sem['display_name']} seed={seed} ===", flush=True)

        char = c.create_character().execute(f"{sem['display_name']} rem")
        c.update_visual_identity().execute(
            char.id,
            {
                "identity_tags": list(sem["identity_tags"]),
                "character_name": sem["character_name"],
                "franchise": sem["franchise"],
            },
        )
        beat = c.create_beat().execute(scene.id, intent=f"gate27-rem {fid}", speaker_id=char.id)
        shot = pipe.plan_shot(beat.id)
        spec = to_anima_render_spec(sem)
        spec["_ignore_saved_anima_positive"] = True
        pipe.update_shot(shot.id, {**spec, "character_id": char.id})

        draft = drafts.ensure_for_shot(shot.id)
        neg = f"{draft.rendered_base_negative}, {rem['negative_extra']}".strip(", ")
        if not draft.rendered_base_negative:
            neg = f"{_DEFAULT_NEG}, {rem['negative_extra']}"
        drafts.update_edits(shot.id, rem["positive"], neg)

        rendered = pipe.render(shot.id, seed=seed)
        attempt = pipe.get_attempt(rendered["generation_attempt_id"])
        assert attempt.seed == seed
        assert attempt.payload["model_id"] == "anima_base"
        assert attempt.payload.get("final_positive_prompt") == rem["positive"]

        asset_id = rendered["output_asset_ids"][0]
        with c.uow() as uow:
            a = uow.assets.get(asset_id)
            assert a is not None
            uri, sha, mime = a.uri, a.sha256, a.mime
        data = c.asset_store.path_for_uri(uri).read_bytes()
        width, height, mean = _assert_image_gate(data)
        assert hashlib.sha256(data).hexdigest() == sha

        prompt_hash = attempt.payload.get("prompt_hash") or compute_prompt_hash(
            rem["positive"], neg
        )

        char_dir = _ARTIFACT_DIR / fid
        char_dir.mkdir(parents=True, exist_ok=True)
        # Keep previous image for side-by-side if present
        prev = char_dir / "image.png"
        if prev.is_file():
            (char_dir / "image_pre_remediation.png").write_bytes(prev.read_bytes())
        (char_dir / "image.png").write_bytes(data)

        manifest = {
            "gate": "anima-gate2_7",
            "variant": "remediation",
            "fixture_id": fid,
            "fixture_name": sem["display_name"],
            "slug": slug,
            "status": "generated",
            "capability": "BaseRender",
            "model_id": "anima_base",
            "workflow_template_id": "anima_base_v1",
            "workflow_hash": attempt.workflow_hash,
            "seed": seed,
            "prompt_hash": prompt_hash,
            "prompt_source": "remediation",
            "remediation_notes": rem["notes"],
            "width": width,
            "height": height,
            "mime": mime or "image/png",
            "sha256": sha,
            "mean_luma": round(mean, 2),
            "comfy_version": comfy_version,
            "commit": commit,
            "character_name": sem["character_name"],
            "franchise": sem["franchise"],
            "final_positive_prompt": rem["positive"],
            "final_negative_prompt": neg,
            "asset_id": asset_id,
            "generation_attempt_id": rendered["generation_attempt_id"],
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }
        (char_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        (_ARTIFACT_DIR / "adopted_prompts" / f"{fid}_{slug}.anima.txt").write_text(
            rem["positive"] + "\n", encoding="utf-8"
        )

        # Checklist scaffolding with expected GT items for rematch
        if fid == "C02":
            items = [
                ("Trigger / character", "open"),
                ("Hair (silver/grey)", "open"),
                ("Eyes (green)", "open"),
                ("Hairstyle", "open"),
                ("Signature accessory (police hat + blue flower)", "open"),
                ("Default outfit (police/capelet/blue shorts)", "open"),
                ("Main colors (white/blue)", "open"),
                ("Silhouette (dog-girl police)", "open"),
            ]
        elif fid == "C04":
            items = [
                ("Trigger / character", "open"),
                ("Hair (blonde side ponytail)", "open"),
                ("Eyes (heterochromia red/yellow)", "open"),
                ("Hairstyle", "open"),
                ("Signature accessory (x ornament)", "open"),
                ("Default outfit", "open"),
                ("Main colors", "open"),
                ("Silhouette", "open"),
            ]
        elif fid == "C06":
            items = [
                ("Trigger / character", "open"),
                ("Hair (pink)", "open"),
                ("Eyes (pink/magenta)", "open"),
                ("Hairstyle (side ponytail + clips)", "open"),
                ("Signature accessory (star/ribbon hair ornament)", "open"),
                ("Default outfit (Mirai idol stage)", "open"),
                ("Main colors (pink/white)", "open"),
                ("Silhouette", "open"),
            ]
        else:
            items = [
                ("Photoreal / live-action look (NOT anime)", "open"),
                ("Adult woman", "open"),
                ("Dark brown hair", "open"),
                ("Dark brown eyes", "open"),
                ("Hairstyle (shoulder-length waves)", "open"),
                ("Casual blouse/skirt", "open"),
                ("Natural skin/lighting", "open"),
                ("No extreme anime bias", "open"),
            ]
        _write_gt_checklist(fid, sem["display_name"], rem, items)

        rematch_rows.append(
            {
                "fixture_id": fid,
                "fixture_name": sem["display_name"],
                "seed": seed,
                "width": width,
                "height": height,
                "sha256": sha,
                "prompt_hash": prompt_hash,
            }
        )

    _rebuild_contact_sheet()

    # Update SUMMARY remediation section (preserve prior human scores table)
    summary_path = _ARTIFACT_DIR / "SUMMARY.md"
    prior = summary_path.read_text(encoding="utf-8") if summary_path.is_file() else ""
    rem_block = [
        "",
        "## Remediation rematch",
        "",
        f"- status: `GENERATED — awaiting human rematch`",
        f"- commit: `{commit}`",
        f"- comfy: `{comfy_version}`",
        f"- recorded_at: `{datetime.now(timezone.utc).isoformat()}`",
        f"- entry: `pnpm test:anima:gate2_7:remediation`",
        f"- seeds unchanged: C02=27002, C04=27004, C06=27006, C11=27011",
        "",
        "| ID | W×H | SHA256 (short) |",
        "|----|-----|----------------|",
    ]
    for r in rematch_rows:
        rem_block.append(
            f"| {r['fixture_id']} | {r['width']}×{r['height']} | `{r['sha256'][:12]}` |"
        )
    rem_block.extend(
        [
            "",
            "### C11 policy note",
            "",
            "Anima Base (`anima_baseV10`) is anime-tuned. Photoreal tags without a "
            "photoreal model/profile may still fail the C11 criterion. If rematch "
            "remains illustrated, exclude C11 from Anima identity PASS and track "
            "photoreal coverage under a separate model profile (Phase 2.1+).",
            "",
            "### Next",
            "",
            "1. Human rematch of C02 / C04 / C06 / C11 on updated `contact_sheet.png`",
            "2. Fill `gt_checklist.md` per 8 GT items + update `human_scores.csv`",
            "3. Require ≥9/11 identifiable and C11 photoreal criterion (or policy carve-out)",
            "4. Only then proceed to A3 Pose Live",
            "",
        ]
    )
    # Append rematch block; keep historical human FAIL above
    if "## Remediation rematch" in prior:
        head = prior.split("## Remediation rematch")[0].rstrip()
        summary_path.write_text(head + "\n" + "\n".join(rem_block), encoding="utf-8")
    else:
        summary_path.write_text(prior.rstrip() + "\n" + "\n".join(rem_block), encoding="utf-8")

    # Mark scores for rematch targets as pending without wiping prior scores
    scores_path = _ARTIFACT_DIR / "human_scores.csv"
    rows = list(csv.DictReader(scores_path.open(encoding="utf-8")))
    fieldnames = list(rows[0].keys()) if rows else [
        "fixture_id",
        "fixture_name",
        "seed",
        "gt_score_0_8",
        "identifiable",
        "catastrophic",
        "notes",
    ]
    if "rematch" not in fieldnames:
        fieldnames.append("rematch")
    rem_ids = set(REMEDIATIONS)
    for row in rows:
        if row["fixture_id"] in rem_ids:
            row["rematch"] = "pending_human"
            row["notes"] = (
                (row.get("notes") or "")
                + " | rematch image generated; awaiting GT rematch"
            ).strip(" |")
        else:
            row.setdefault("rematch", "unchanged")
    with scores_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    assert len(rematch_rows) == 4
