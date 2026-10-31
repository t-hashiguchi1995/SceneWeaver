"""Gate 2.7 — Anima Full Character Coverage (C01–C11).

Entry: ``pnpm test:anima:gate2_7``

Automatic PASS = 11/11 PNG ≥512 + provenance + contact sheet + scores CSV scaffold.
Human PASS = GT checklist on contact sheet (≥9/11 identifiable) — filled after review.
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
from creator_studio.domain.prompt import ANIMA_COMPILER_SOURCE_REF, compute_prompt_hash
from creator_studio.infrastructure.container import Container, reset_container
from creator_studio.infrastructure.db.migrate import upgrade_head
from creator_studio.infrastructure.db.session import reset_engine
from creator_studio.infrastructure.settings import Settings, clear_settings_cache
from creator_studio.infrastructure.settings.config import REPO_ROOT
from tests.live.anima_character_semantics import (
    GATE27_PRIMARY,
    GATE27_SEEDS,
    GATE27_SLUGS,
    to_anima_render_spec,
)
from tests.live.test_moss_sft_live import _assert_image_gate

pytestmark = pytest.mark.skipif(
    os.environ.get("SCENEWEAVER_ANIMA_LIVE", "").lower() not in {"1", "true", "yes"}
    and os.environ.get("SCENEWEAVER_GATE27_LIVE", "").lower() not in {"1", "true", "yes"},
    reason="Set SCENEWEAVER_GATE27_LIVE=1 (or SCENEWEAVER_ANIMA_LIVE=1) "
    "or run: pnpm test:anima:gate2_7",
)

_ARTIFACT_DIR = REPO_ROOT / "docs" / "validation" / "anima-gate2_7"
_ADOPTED_26 = REPO_ROOT / "docs" / "validation" / "anima-gate2_6" / "adopted_prompts"
_MIN_EDGE = 512
_SHEET_THUMB = 280
_SHEET_PAD = 8
_LABEL_H = 36
_REQUIRED_CKPT = "anima_baseV10.safetensors"
_COLS = 4


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
    runtime = tmp_path / "runtime-anima-gate2_7"
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
    version = _require_anima_runtime(comfy_url)
    return Container(settings), version


def _render_patch(sem: dict) -> dict:
    spec = to_anima_render_spec(sem)  # type: ignore[arg-type]
    spec["_ignore_saved_anima_positive"] = True
    return spec


def _load_adopted_26(fid: str, slug: str) -> str | None:
    path = _ADOPTED_26 / f"{fid}_{slug}.anima.txt"
    if not path.is_file():
        # Gate 2.6 used firefly slug for C10
        alt = _ADOPTED_26 / f"{fid}_firefly.anima.txt" if fid == "C10" else None
        if alt and alt.is_file():
            return alt.read_text(encoding="utf-8").strip()
        return None
    return path.read_text(encoding="utf-8").strip()


def _build_contact_sheet(rows: list[dict], out_path: Path) -> None:
    n = len(rows)
    cols = _COLS
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
        img = Image.open(io.BytesIO(row["png_bytes"]))
        img.load()
        thumb = img.convert("RGB")
        thumb.thumbnail((cell_w, _SHEET_THUMB))
        ox = x0 + (cell_w - thumb.width) // 2
        oy = y0 + (_SHEET_THUMB - thumb.height) // 2
        sheet.paste(thumb, (ox, oy))
        label = f"{row['fixture_id']} {row['fixture_name'][:10]} s{row['seed']}"
        draw.text((x0 + 4, y0 + _SHEET_THUMB + 4), label, fill=(230, 230, 235), font=font)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path, format="PNG")


def _write_summary(rows: list[dict], *, comfy_version: str, commit: str, auto_ok: bool) -> None:
    lines = [
        "# Gate 2.7 — Anima Full Character Coverage",
        "",
        f"- status_auto: `{'PASS' if auto_ok else 'FAIL'}`",
        f"- status_human: `PENDING`（contact sheet を GT 採点）",
        f"- commit: `{commit}`",
        f"- comfy: `{comfy_version}`",
        f"- recorded_at: `{datetime.now(timezone.utc).isoformat()}`",
        f"- entry: `pnpm test:anima:gate2_7`",
        "",
        "## Roster",
        "",
        "| ID | Name | Seed | Prompt | W×H | Trigger | Auto |",
        "|----|------|------|--------|-----|---------|------|",
    ]
    for r in rows:
        lines.append(
            f"| {r['fixture_id']} | {r['fixture_name']} | {r['seed']} | "
            f"{r['prompt_source']} | {r['width']}×{r['height']} | "
            f"{'yes' if r['trigger_ok'] else 'no'} | {r['auto_status']} |"
        )
    lines.extend(
        [
            "",
            "## Human PASS checklist",
            "",
            "- [ ] catastrophic failure なし",
            "- [ ] ≥9/11 が GT 主要項目で識別可能",
            "- [ ] contact sheet で別人取り違えが支配的でない",
            "- [ ] C11 が極端な anime 化で破綻しない",
            "",
            "## Next",
            "",
            "- Human scores → `human_scores.csv`",
            "- PASS 後 → A3 Pose Live P01–P05",
            "",
        ]
    )
    (_ARTIFACT_DIR / "SUMMARY.md").write_text("\n".join(lines), encoding="utf-8")


def test_gate2_7_full_character_coverage(live_container: tuple[Container, str]) -> None:
    c, comfy_version = live_container
    commit = _git_commit()
    assert len(GATE27_PRIMARY) == 11
    assert set(GATE27_SEEDS) == {s["fixture_id"] for s in GATE27_PRIMARY}

    _ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    adopted_out = _ARTIFACT_DIR / "adopted_prompts"
    adopted_out.mkdir(parents=True, exist_ok=True)

    project = c.create_project().execute(CreateProjectCommand(title="Anima Gate2.7"))
    scene = c.create_scene().execute(project.id, "Studio")
    pipe = c.shot_pipeline()
    drafts = c.prompt_draft_service()

    results: list[dict] = []
    for sem in GATE27_PRIMARY:
        fid = sem["fixture_id"]
        slug = GATE27_SLUGS[fid]
        seed = GATE27_SEEDS[fid]
        print(f"\n=== {fid} {sem['display_name']} seed={seed} ===", flush=True)

        char = c.create_character().execute(sem["display_name"])
        c.update_visual_identity().execute(
            char.id,
            {
                "identity_tags": list(sem["identity_tags"]),
                "character_name": sem["character_name"],
                "franchise": sem["franchise"],
                "hair": next((t for t in sem["identity_tags"] if "hair" in t), ""),
                "eyes": next((t for t in sem["identity_tags"] if "eyes" in t), ""),
            },
        )
        beat = c.create_beat().execute(scene.id, intent=f"gate27 {fid}", speaker_id=char.id)
        shot = pipe.plan_shot(beat.id)
        pipe.update_shot(shot.id, {**_render_patch(sem), "character_id": char.id})

        draft = drafts.ensure_for_shot(shot.id)
        assert draft.source_ref == ANIMA_COMPILER_SOURCE_REF
        base_pos = draft.rendered_base_positive
        neg = draft.rendered_base_negative

        adopted = _load_adopted_26(fid, slug)
        if adopted:
            prompt_source = "gate26_adopted"
            final_pos = adopted
            drafts.update_edits(shot.id, final_pos, neg)
        else:
            prompt_source = "compiled"
            final_pos = base_pos

        # Trigger / character identity must remain in the final prompt
        if fid == "C11":
            trigger_ok = "photorealistic" in final_pos.lower() or "realistic" in final_pos.lower()
            assert "nsfw" not in final_pos.lower()
        else:
            trigger_ok = sem["character_name"] in final_pos
            if sem["franchise"] != "original":
                trigger_ok = trigger_ok and sem["franchise"] in final_pos
            assert trigger_ok, f"{fid} missing trigger in prompt"

        rendered = pipe.render(shot.id, seed=seed)
        assert rendered["output_asset_ids"]
        attempt = pipe.get_attempt(rendered["generation_attempt_id"])
        assert attempt.seed == seed
        assert attempt.payload["capability"] == "BaseRender"
        assert attempt.payload["model_id"] == "anima_base"
        assert attempt.payload["render_snapshot"]["workflow_template_id"] == "anima_base_v1"

        asset_id = rendered["output_asset_ids"][0]
        with c.uow() as uow:
            a = uow.assets.get(asset_id)
            assert a is not None
            uri, sha, mime = a.uri, a.sha256, a.mime
        data = c.asset_store.path_for_uri(uri).read_bytes()
        width, height, mean = _assert_image_gate(data)
        assert hashlib.sha256(data).hexdigest() == sha

        prompt_hash = attempt.payload.get("prompt_hash") or compute_prompt_hash(
            attempt.payload.get("final_positive_prompt") or final_pos,
            attempt.payload.get("final_negative_prompt") or neg,
        )

        char_dir = _ARTIFACT_DIR / fid
        char_dir.mkdir(parents=True, exist_ok=True)
        png_path = char_dir / "image.png"
        png_path.write_bytes(data)
        manifest = {
            "gate": "anima-gate2_7",
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
            "prompt_source": prompt_source,
            "width": width,
            "height": height,
            "mime": mime or "image/png",
            "sha256": sha,
            "mean_luma": round(mean, 2),
            "comfy_version": comfy_version,
            "commit": commit,
            "character_name": sem["character_name"],
            "franchise": sem["franchise"],
            "animadex_url": sem.get("animadex_url") or "",
            "final_positive_prompt": attempt.payload.get("final_positive_prompt") or final_pos,
            "asset_id": asset_id,
            "generation_attempt_id": rendered["generation_attempt_id"],
            "trigger_ok": trigger_ok,
        }
        (char_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        (char_dir / "gt_checklist.md").write_text(
            "\n".join(
                [
                    f"# GT checklist — {fid} {sem['display_name']}",
                    "",
                    f"- ANIMADEX: {sem.get('animadex_url') or 'n/a (original)'}",
                    f"- Prompt source: `{prompt_source}`",
                    "",
                    "- [ ] Trigger / character recognizable",
                    "- [ ] Hair",
                    "- [ ] Eyes",
                    "- [ ] Hairstyle",
                    "- [ ] Signature accessory",
                    "- [ ] Default outfit",
                    "- [ ] Main colors",
                    "- [ ] Silhouette",
                    "",
                    "Score (0–8): _",
                    "Notes:",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        # Persist prompt used for this gate (may equal Gate 2.6 adopted)
        (adopted_out / f"{fid}_{slug}.anima.txt").write_text(final_pos + "\n", encoding="utf-8")

        results.append(
            {
                "fixture_id": fid,
                "fixture_name": sem["display_name"],
                "slug": slug,
                "seed": seed,
                "prompt_source": prompt_source,
                "width": width,
                "height": height,
                "trigger_ok": trigger_ok,
                "auto_status": "PASS",
                "png_bytes": data,
                "sha256": sha,
                "prompt_hash": prompt_hash,
            }
        )

    sheet_path = _ARTIFACT_DIR / "contact_sheet.png"
    _build_contact_sheet(results, sheet_path)

    scores_path = _ARTIFACT_DIR / "human_scores.csv"
    with scores_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "fixture_id",
                "fixture_name",
                "seed",
                "gt_score_0_8",
                "identifiable",
                "catastrophic",
                "notes",
            ],
        )
        w.writeheader()
        for r in results:
            w.writerow(
                {
                    "fixture_id": r["fixture_id"],
                    "fixture_name": r["fixture_name"],
                    "seed": r["seed"],
                    "gt_score_0_8": "",
                    "identifiable": "",
                    "catastrophic": "",
                    "notes": "",
                }
            )

    auto_ok = len(results) == 11 and all(r["auto_status"] == "PASS" for r in results)
    _write_summary(results, comfy_version=comfy_version, commit=commit, auto_ok=auto_ok)
    assert auto_ok
    assert sheet_path.is_file() and sheet_path.stat().st_size > 10_000
