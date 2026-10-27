"""Gate 2.6 — Anima Prompt Quality Baseline (Base → Edited, same seed, Δ).

Entry: ``pnpm test:anima:gate2_6``

Hard PASS = 5/5 Base+Edited comparable + adopted prompts + hashes + contact sheet.
Human PASS = ≥4/5 Δ>0 and no clear regression (scores filled after visual review).
"""

from __future__ import annotations

import csv
import difflib
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
from tests.live.anima_character_semantics import GATE26_PRIMARY, to_anima_render_spec
from tests.live.anima_gate2_6_edits import EDITS, GATE26_SEEDS
from tests.live.test_moss_sft_live import _assert_image_gate

pytestmark = pytest.mark.skipif(
    os.environ.get("SCENEWEAVER_MOSS_LIVE", "").lower() not in {"1", "true", "yes"}
    and os.environ.get("SCENEWEAVER_ANIMA_LIVE", "").lower() not in {"1", "true", "yes"},
    reason="Set SCENEWEAVER_ANIMA_LIVE=1 (or SCENEWEAVER_MOSS_LIVE=1) or run: pnpm test:anima:gate2_6",
)

_ARTIFACT_DIR = REPO_ROOT / "docs" / "validation" / "anima-gate2_6"
_MIN_EDGE = 512
_SHEET_THUMB = 320
_SHEET_PAD = 10
_LABEL_H = 26
_REQUIRED_CKPT = "anima_baseV10.safetensors"


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
        pytest.fail(
            f"ENV: Anima checkpoint missing ({_REQUIRED_CKPT}). "
            f"comfyui_version={version!r}"
        )
    return version or "unknown"


@pytest.fixture()
def live_container(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Container, str]:
    runtime = tmp_path / "runtime-anima-gate2_6"
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
    # Force BaseRender path; ignore any saved prompt during Base compile.
    spec["_ignore_saved_anima_positive"] = True
    return spec


def _prompt_diff(base: str, edited: str) -> str:
    return "\n".join(
        difflib.unified_diff(
            base.split(", "),
            edited.split(", "),
            fromfile="base",
            tofile="edited",
            lineterm="",
        )
    )


def _build_contact_sheet_2col(rows: list[dict], out_path: Path) -> None:
    """2 columns: Base | Edited, one row per character."""
    cols = 2
    n = len(rows)
    cell_w = _SHEET_THUMB
    cell_h = _SHEET_THUMB + _LABEL_H
    sheet_w = cols * cell_w + (cols + 1) * _SHEET_PAD
    sheet_h = n * cell_h + (n + 1) * _SHEET_PAD
    sheet = Image.new("RGB", (sheet_w, sheet_h), (32, 32, 36))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.load_default()
    except OSError:
        font = None

    for r, row in enumerate(rows):
        for c, key in enumerate(("base_png", "edited_png")):
            x0 = _SHEET_PAD + c * (cell_w + _SHEET_PAD)
            y0 = _SHEET_PAD + r * (cell_h + _SHEET_PAD)
            png = Image.open(row[key]).convert("RGB")
            png.thumbnail((_SHEET_THUMB, _SHEET_THUMB), Image.Resampling.LANCZOS)
            ox = x0 + (_SHEET_THUMB - png.width) // 2
            oy = y0 + (_SHEET_THUMB - png.height) // 2
            sheet.paste(png, (ox, oy))
            label = f"{row['fixture_id']} {'Base' if c == 0 else 'Edited'}  seed={row['seed']}"
            draw.rectangle(
                [x0, y0 + _SHEET_THUMB, x0 + cell_w, y0 + cell_h],
                fill=(24, 24, 28),
            )
            draw.text(
                (x0 + 6, y0 + _SHEET_THUMB + 6),
                label,
                fill=(230, 230, 235),
                font=font,
            )
    sheet.save(out_path, format="PNG")


def _write_scores_csv(path: Path, rows: list[dict]) -> None:
    fields = [
        "fixture_id",
        "fixture_name",
        "seed",
        "variant",
        "identity",
        "outfit",
        "color",
        "accessories",
        "overall",
        "total",
        "delta_total",
        "notes",
    ]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            scores = row.get("scores") or {}
            for variant in ("base", "edited"):
                s = scores.get(variant) or {}
                writer.writerow(
                    {
                        "fixture_id": row["fixture_id"],
                        "fixture_name": row["fixture_name"],
                        "seed": row["seed"],
                        "variant": variant,
                        "identity": s.get("identity", ""),
                        "outfit": s.get("outfit", ""),
                        "color": s.get("color", ""),
                        "accessories": s.get("accessories", ""),
                        "overall": s.get("overall", ""),
                        "total": s.get("total", ""),
                        "delta_total": scores.get("delta", "") if variant == "edited" else "",
                        "notes": row.get("edit_notes", "") if variant == "edited" else "auto-compile base",
                    }
                )


def _write_summary(
    path: Path,
    *,
    commit: str,
    comfy_version: str,
    rows: list[dict],
    auto_ok: bool,
    human_status: str,
) -> None:
    improved = sum(
        1
        for r in rows
        if isinstance((r.get("scores") or {}).get("delta"), (int, float))
        and (r["scores"]["delta"] or 0) > 0
    )
    scored = sum(1 for r in rows if (r.get("scores") or {}).get("delta") is not None)
    lines = [
        "# Anima Gate 2.6 — Prompt Quality Baseline SUMMARY",
        "",
        "## Run metadata",
        "",
        f"- date: `{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}`",
        f"- commit: `{commit}`",
        "- model_id: `anima_base`",
        "- workflow_template_id: `anima_base_v1`",
        "- capability: `BaseRender`",
        f"- comfy_version: `{comfy_version}`",
        "- seed policy: fixed per fixture (C01=26001 … C10=26010); Base == Edited seed",
        "",
        "## Flow",
        "",
        "```text",
        "Semantic Spec → Anima Base compile → Base gen",
        "  → Prompt edit → same seed regen → Base|Edited compare → adopt Final Prompt",
        "```",
        "",
        "## Automatic gate",
        "",
        f"- Base+Edited pairs: **{len(rows)} / 5**",
        "- contact_sheet_base_vs_edited.png: 2-col Base | Edited",
        "- adopted_prompts/: Final Prompt per character",
        "- manifests: prompt_hash / seed / model / workflow / provenance",
        "",
        "### Automatic PASS",
        "",
        "- 5/5 Base generated",
        "- 5/5 Edited generated (same seed)",
        "- 5/5 comparable artifacts",
        "- Final Prompt saved (character + adopted_prompts)",
        "- prompt_hash / provenance present",
        "",
        "### Human PASS (improvement)",
        "",
        "- ≥4/5 characters with Δ > 0",
        "- no clear regression (large negative Δ)",
        "",
        "## Per fixture",
        "",
        "| ID | Name | Seed | Auto | Base | Edited | Δ | Notes |",
        "|----|------|------|------|------|--------|---|-------|",
    ]
    for r in rows:
        sc = r.get("scores") or {}
        btot = (sc.get("base") or {}).get("total", "_")
        etot = (sc.get("edited") or {}).get("total", "_")
        delta = sc.get("delta", "_")
        lines.append(
            f"| {r['fixture_id']} | {r['fixture_name']} | {r['seed']} | "
            f"{r['auto_status']} | {btot} | {etot} | {delta} | {r.get('edit_notes', '')[:48]} |"
        )
    lines.extend(
        [
            "",
            "## Aggregate",
            "",
            f"- pairs: {len(rows)}",
            f"- scored: {scored}",
            f"- improved (Δ>0): {improved}",
            "",
            "## Status",
            "",
            f"- automatic: `{'PASS' if auto_ok else 'FAIL'}`",
            f"- human: `{human_status}`",
            "",
            "## Next",
            "",
            "- Gate 3 outfit isolation can reuse adopted Anima prompts "
            "(reduces “wrong character” noise).",
            "- Pose Gallery live validation **after** this gate PASS.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def _save_variant_artifacts(
    *,
    char_dir: Path,
    variant: str,
    data: bytes,
    manifest: dict,
) -> Path:
    png_path = char_dir / f"{variant}.png"
    png_path.write_bytes(data)
    man_path = char_dir / f"{variant}.manifest.json"
    man_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return png_path


def test_gate2_6_prompt_quality_baseline(live_container: tuple[Container, str]) -> None:
    c, comfy_version = live_container
    commit = _git_commit()
    _ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    adopted_dir = _ARTIFACT_DIR / "adopted_prompts"
    adopted_dir.mkdir(parents=True, exist_ok=True)
    # Drop stale adopted files from prior runs (e.g. C10 slug rename hotaru→firefly).
    for stale in adopted_dir.glob("*"):
        if stale.is_file():
            stale.unlink()

    project = c.create_project().execute(CreateProjectCommand(title="Anima Gate2.6"))
    scene = c.create_scene().execute(project.id, "Studio")
    pipe = c.shot_pipeline()
    drafts = c.prompt_draft_service()

    results: list[dict] = []
    for sem in GATE26_PRIMARY:
        fid = sem["fixture_id"]
        edit = EDITS[fid]
        seed = GATE26_SEEDS[fid]
        assert edit["seed"] == seed

        char = c.create_character().execute(sem["display_name"])
        c.update_visual_identity().execute(
            char.id,
            {
                "identity_tags": list(sem["identity_tags"]),
                "character_name": sem["character_name"],
                "franchise": sem["franchise"],
                "hair": sem["identity_tags"][0] if sem["identity_tags"] else "",
                "eyes": next((t for t in sem["identity_tags"] if "eyes" in t), ""),
            },
        )
        beat = c.create_beat().execute(
            scene.id, intent=f"gate26 {fid}", speaker_id=char.id
        )
        shot = pipe.plan_shot(beat.id)
        pipe.update_shot(shot.id, {**_render_patch(sem), "character_id": char.id})

        # --- Base ---
        draft = drafts.ensure_for_shot(shot.id)
        assert draft.source_ref == ANIMA_COMPILER_SOURCE_REF
        base_pos = draft.rendered_base_positive
        assert sem["character_name"] in base_pos
        if sem["franchise"] != "original":
            assert sem["franchise"] in base_pos
        assert "nsfw" not in base_pos.lower()

        rendered_base = pipe.render(shot.id, seed=seed)
        assert rendered_base["output_asset_ids"]
        attempt_b = pipe.get_attempt(rendered_base["generation_attempt_id"])
        assert attempt_b.seed == seed
        assert attempt_b.payload["capability"] == "BaseRender"
        assert attempt_b.payload["model_id"] == "anima_base"
        assert attempt_b.payload["render_snapshot"]["workflow_template_id"] == "anima_base_v1"

        asset_b = rendered_base["output_asset_ids"][0]
        with c.uow() as uow:
            a = uow.assets.get(asset_b)
            assert a is not None
            uri_b, sha_b, mime_b = a.uri, a.sha256, a.mime
        data_b = c.asset_store.path_for_uri(uri_b).read_bytes()
        w_b, h_b, mean_b = _assert_image_gate(data_b)
        assert w_b >= _MIN_EDGE and h_b >= _MIN_EDGE
        assert hashlib.sha256(data_b).hexdigest() == sha_b

        base_hash = attempt_b.payload.get("prompt_hash") or compute_prompt_hash(
            attempt_b.payload.get("final_positive_prompt") or base_pos,
            attempt_b.payload.get("final_negative_prompt") or draft.rendered_base_negative,
        )

        char_dir = _ARTIFACT_DIR / fid
        char_dir.mkdir(parents=True, exist_ok=True)
        base_png = _save_variant_artifacts(
            char_dir=char_dir,
            variant="base",
            data=data_b,
            manifest={
                "gate": "anima-gate2_6",
                "fixture_id": fid,
                "fixture_name": sem["display_name"],
                "variant": "base",
                "status": "generated",
                "capability": "BaseRender",
                "model_id": "anima_base",
                "workflow_template_id": "anima_base_v1",
                "workflow_hash": attempt_b.workflow_hash,
                "seed": seed,
                "prompt_hash": base_hash,
                "width": w_b,
                "height": h_b,
                "mime": mime_b or "image/png",
                "sha256": sha_b,
                "external_job_ref": attempt_b.payload.get("external_job_ref")
                or rendered_base.get("external_job_ref"),
                "comfy_version": comfy_version,
                "mean_luma": round(mean_b, 2),
                "source_ref": draft.source_ref,
                "final_positive_prompt": attempt_b.payload.get("final_positive_prompt")
                or base_pos,
                "character_name": sem["character_name"],
                "franchise": sem["franchise"],
                "commit": commit,
                "asset_id": asset_b,
                "generation_attempt_id": rendered_base["generation_attempt_id"],
            },
        )

        # --- Edited (same seed) ---
        edited_pos = edit["edited_positive"]
        drafts.update_edits(shot.id, edited_pos, draft.rendered_base_negative)
        rendered_e = pipe.render(shot.id, seed=seed)
        assert rendered_e["output_asset_ids"]
        attempt_e = pipe.get_attempt(rendered_e["generation_attempt_id"])
        assert attempt_e.seed == seed
        assert attempt_e.payload.get("modified") is True
        assert attempt_e.payload.get("final_positive_prompt") == edited_pos

        asset_e = rendered_e["output_asset_ids"][0]
        with c.uow() as uow:
            a = uow.assets.get(asset_e)
            assert a is not None
            uri_e, sha_e, mime_e = a.uri, a.sha256, a.mime
        data_e = c.asset_store.path_for_uri(uri_e).read_bytes()
        w_e, h_e, mean_e = _assert_image_gate(data_e)
        assert hashlib.sha256(data_e).hexdigest() == sha_e

        edited_hash = attempt_e.payload.get("prompt_hash") or compute_prompt_hash(
            edited_pos,
            attempt_e.payload.get("final_negative_prompt") or draft.rendered_base_negative,
        )
        assert edited_hash != base_hash

        edited_png = _save_variant_artifacts(
            char_dir=char_dir,
            variant="edited",
            data=data_e,
            manifest={
                "gate": "anima-gate2_6",
                "fixture_id": fid,
                "fixture_name": sem["display_name"],
                "variant": "edited",
                "status": "generated",
                "capability": "BaseRender",
                "model_id": "anima_base",
                "workflow_template_id": "anima_base_v1",
                "workflow_hash": attempt_e.workflow_hash,
                "seed": seed,
                "prompt_hash": edited_hash,
                "base_prompt_hash": base_hash,
                "width": w_e,
                "height": h_e,
                "mime": mime_e or "image/png",
                "sha256": sha_e,
                "external_job_ref": attempt_e.payload.get("external_job_ref")
                or rendered_e.get("external_job_ref"),
                "comfy_version": comfy_version,
                "mean_luma": round(mean_e, 2),
                "source_ref": draft.source_ref,
                "modified": True,
                "final_positive_prompt": edited_pos,
                "edit_notes": edit["edit_notes"],
                "character_name": sem["character_name"],
                "franchise": sem["franchise"],
                "commit": commit,
                "asset_id": asset_e,
                "generation_attempt_id": rendered_e["generation_attempt_id"],
            },
        )

        (char_dir / "prompt_diff.txt").write_text(
            _prompt_diff(base_pos, edited_pos) + "\n", encoding="utf-8"
        )

        # Adopt Final Prompt onto Character + artifact file.
        c.update_visual_identity().execute(
            char.id, {"saved_anima_positive": edited_pos}
        )
        with c.uow() as uow:
            saved_char = uow.characters.get(char.id)
            assert saved_char is not None
            assert saved_char.visual_identity.saved_anima_positive == edited_pos

        adopted_name = f"{fid}_{edit['slug']}.anima.txt"
        (adopted_dir / adopted_name).write_text(edited_pos + "\n", encoding="utf-8")
        (adopted_dir / f"{fid}_{edit['slug']}.provenance.json").write_text(
            json.dumps(
                {
                    "fixture_id": fid,
                    "prompt_hash": edited_hash,
                    "base_prompt_hash": base_hash,
                    "seed": seed,
                    "model_id": "anima_base",
                    "workflow_template_id": "anima_base_v1",
                    "capability": "BaseRender",
                    "character_name": sem["character_name"],
                    "franchise": sem["franchise"],
                    "adopted_file": adopted_name,
                    "commit": commit,
                },
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

        results.append(
            {
                "fixture_id": fid,
                "fixture_name": sem["display_name"],
                "seed": seed,
                "auto_status": "passed",
                "base_png": base_png,
                "edited_png": edited_png,
                "edit_notes": edit["edit_notes"],
                "base_prompt_hash": base_hash,
                "edited_prompt_hash": edited_hash,
                "scores": {},  # filled by post-run scoring script / review
            }
        )

    assert len(results) == 5
    sheet_path = _ARTIFACT_DIR / "contact_sheet_base_vs_edited.png"
    _build_contact_sheet_2col(results, sheet_path)
    assert sheet_path.exists() and sheet_path.stat().st_size > 10_000

    scores_path = _ARTIFACT_DIR / "human_scores.csv"
    _write_scores_csv(scores_path, results)
    summary_path = _ARTIFACT_DIR / "SUMMARY.md"
    _write_summary(
        summary_path,
        commit=commit,
        comfy_version=comfy_version,
        rows=results,
        auto_ok=True,
        human_status="PENDING",
    )
    assert summary_path.exists()
    assert scores_path.exists()
    assert len(list(adopted_dir.glob("*.anima.txt"))) == 5
