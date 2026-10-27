"""Gate 2.5 — Primary target fixture smoke (11 characters).

Entry: ``pnpm test:moss:gate2_5``

Automatic PASS = all 11 PNG + manifests + contact_sheet.png + SUMMARY.md + human_scores.csv.
Human likeness scores are recorded as placeholders for review (not automatic gate).
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont

from creator_studio.application.projects.create_project import CreateProjectCommand
from creator_studio.domain.prompt import MOSS_COMPILER_SOURCE_REF, compute_prompt_hash
from creator_studio.infrastructure.container import Container, reset_container
from creator_studio.infrastructure.db.migrate import upgrade_head
from creator_studio.infrastructure.db.session import reset_engine
from creator_studio.infrastructure.settings import Settings, clear_settings_cache
from creator_studio.infrastructure.settings.config import REPO_ROOT
from tests.live.moss_sft_gate2_5_fixtures import PRIMARY, image_basename, render_patch
from tests.live.test_moss_sft_live import _assert_image_gate, _require_moss_runtime

pytestmark = pytest.mark.skipif(
    os.environ.get("SCENEWEAVER_MOSS_LIVE", "").lower() not in {"1", "true", "yes"},
    reason="Set SCENEWEAVER_MOSS_LIVE=1 or run: pnpm test:moss:gate2_5",
)

_ARTIFACT_DIR = REPO_ROOT / "docs" / "validation" / "moss-sft-gate2_5"
_MIN_EDGE = 512
_SHEET_THUMB = 384
_SHEET_COLS = 4
_SHEET_PAD = 12
_LABEL_H = 28


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


@pytest.fixture()
def live_container(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Container, str]:
    runtime = tmp_path / "runtime-moss-gate2_5"
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
    version = _require_moss_runtime(comfy_url)
    return Container(settings), version


def _build_contact_sheet(rows: list[dict], out_path: Path) -> None:
    n = len(rows)
    cols = _SHEET_COLS
    grid_rows = (n + cols - 1) // cols
    cell_w = _SHEET_THUMB
    cell_h = _SHEET_THUMB + _LABEL_H
    sheet_w = cols * cell_w + (cols + 1) * _SHEET_PAD
    sheet_h = grid_rows * cell_h + (grid_rows + 1) * _SHEET_PAD
    sheet = Image.new("RGB", (sheet_w, sheet_h), (32, 32, 36))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.load_default()
    except OSError:
        font = None

    for idx, row in enumerate(rows):
        r, c = divmod(idx, cols)
        x0 = _SHEET_PAD + c * (cell_w + _SHEET_PAD)
        y0 = _SHEET_PAD + r * (cell_h + _SHEET_PAD)
        png = Image.open(row["png_path"]).convert("RGB")
        png.thumbnail((_SHEET_THUMB, _SHEET_THUMB), Image.Resampling.LANCZOS)
        ox = x0 + (_SHEET_THUMB - png.width) // 2
        oy = y0 + (_SHEET_THUMB - png.height) // 2
        sheet.paste(png, (ox, oy))
        label = f"{row['fixture_id']}  seed={row['seed']}"
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


def _write_human_scores_csv(path: Path, fixtures: list[dict]) -> None:
    fields = [
        "fixture_id",
        "fixture_name",
        "seed",
        "auto_status",
        "valid_image",
        "hair",
        "eyes",
        "outfit",
        "pose_framing",
        "anatomy",
        "identity_impression",
        "score_total",
        "human_pass",
        "notes",
    ]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for fx in fixtures:
            writer.writerow(
                {
                    "fixture_id": fx["fixture_id"],
                    "fixture_name": fx["fixture_name"],
                    "seed": fx["seed"],
                    "auto_status": fx["auto_status"],
                    "valid_image": "",
                    "hair": "",
                    "eyes": "",
                    "outfit": "",
                    "pose_framing": "",
                    "anatomy": "",
                    "identity_impression": "",
                    "score_total": "",
                    "human_pass": "",
                    "notes": "pending human review",
                }
            )


def _write_summary(
    path: Path,
    *,
    commit: str,
    comfy_version: str,
    fixtures: list[dict],
) -> None:
    auto_ok = sum(1 for f in fixtures if f["auto_status"] == "passed")
    lines = [
        "# MOSS-SFT Gate 2.5 — SUMMARY",
        "",
        "## Run metadata",
        "",
        f"- date: `{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}`",
        f"- commit: `{commit}`",
        "- model_id: `moss_image_sft`",
        "- workflow_template_id: `moss_sft_v1`",
        "- capability: `LayoutGuidedRender`",
        f"- comfy_version: `{comfy_version}`",
        "- resolution: `1024x1024`",
        "- seed policy: fixed per fixture_id (C01=20101 … C11=20111)",
        "- sampling: OpenMOSS 50 / CFG 3 / euler / sgm_uniform / shift 5 / SLG 22",
        "",
        "## Automatic gate",
        "",
        f"- fixtures generated: **{auto_ok} / {len(fixtures)}**",
        "- contact_sheet.png: present (see artifact dir)",
        "- human_scores.csv: template written (fill after visual review)",
        "",
        "### Automatic PASS criteria",
        "",
        "- 11/11 PNG decodeable ≥512",
        "- 11/11 manifests with correct fixture_id / seed / model / workflow",
        "- contact_sheet.png + SUMMARY.md + human_scores.csv",
        "",
        "### Human PASS criteria (soft — fill after review)",
        "",
        "- catastrophic failure なし",
        "- 各 fixture が最低限識別可能",
        "- 主要特徴が概ね追える",
        "- 全員同顔問題が支配的でない",
        "- 参考ライン: 11中9以上 human pass / 平均 5/8 以上 / C11 が極端に崩れない",
        "",
        "## Per fixture",
        "",
        "| ID | Name | Seed | Auto | Score | Notes |",
        "|----|------|------|------|-------|-------|",
    ]
    for fx in fixtures:
        lines.append(
            f"| {fx['fixture_id']} | {fx['fixture_name']} | {fx['seed']} | "
            f"{fx['auto_status']} | _(pending)_ | {fx.get('short_notes', '')} |"
        )
    lines.extend(
        [
            "",
            "## Aggregate",
            "",
            f"- total fixtures: {len(fixtures)}",
            f"- auto passed: {auto_ok}",
            f"- auto failed: {len(fixtures) - auto_ok}",
            "- average score: _(fill after human review)_",
            "- human passed: _(fill)_",
            "",
            "## Common failure patterns (checklist for reviewer)",
            "",
            "- [ ] face homogenization",
            "- [ ] eye color drift",
            "- [ ] outfit simplification",
            "- [ ] accessory omission (crown / hat / ribbons)",
            "- [ ] background over-generation",
            "- [ ] anime bias on C11",
            "- [ ] pose stiffness",
            "",
            "## Contact sheet review guide",
            "",
            "1. Face homogenization — especially C01/C04/C05/C08/C09 differences",
            "2. Color collapse — hair / eyes / outfit base colors",
            "3. Silhouette — Elaina hat, Homura vs Madoka, Hotaru SF, C11 photoreal",
            "4. Style drift — C11 anime-leaning? anime side accidentally photoreal?",
            "",
            "## Status",
            "",
            f"- automatic: `{'PASS' if auto_ok == len(fixtures) else 'FAIL'}`",
            "- human: `PENDING`",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def test_gate2_5_primary_fixture_smoke(live_container: tuple[Container, str]) -> None:
    c, comfy_version = live_container
    commit = _git_commit()
    _ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    project = c.create_project().execute(CreateProjectCommand(title="MOSS Gate2.5"))
    scene = c.create_scene().execute(project.id, "Studio")
    pipe = c.shot_pipeline()

    results: list[dict] = []
    for fx in PRIMARY:
        char = c.create_character().execute(fx["fixture_name"])
        beat = c.create_beat().execute(
            scene.id, intent=f"portrait {fx['fixture_id']}", speaker_id=char.id
        )
        shot = pipe.plan_shot(beat.id)
        pipe.update_shot(shot.id, render_patch(fx))
        draft = c.prompt_draft_service().ensure_for_shot(shot.id)
        assert draft.source_ref == MOSS_COMPILER_SOURCE_REF
        for marker in ("safe", "@fuzichoco", "@rella", "score_9"):
            assert marker not in draft.rendered_base_positive

        seed = fx["seed"]
        rendered = pipe.render(shot.id, seed=seed)
        assert rendered["output_asset_ids"]
        attempt = pipe.get_attempt(rendered["generation_attempt_id"])
        assert attempt.seed == seed
        assert attempt.payload["capability"] == "LayoutGuidedRender"
        assert attempt.payload["model_id"] == "moss_image_sft"
        assert attempt.payload["render_snapshot"]["workflow_template_id"] == "moss_sft_v1"

        asset_id = rendered["output_asset_ids"][0]
        with c.uow() as uow:
            asset = uow.assets.get(asset_id)
            assert asset is not None
            uri = asset.uri
            sha256 = asset.sha256
            mime = asset.mime
        data = c.asset_store.path_for_uri(uri).read_bytes()
        width, height, mean = _assert_image_gate(data)
        assert width >= _MIN_EDGE and height >= _MIN_EDGE

        prompt_hash = attempt.payload.get("prompt_hash") or compute_prompt_hash(
            attempt.payload.get("final_positive_prompt") or draft.rendered_base_positive,
            attempt.payload.get("final_negative_prompt") or draft.rendered_base_negative,
        )
        image_file = image_basename(fx)
        png_path = _ARTIFACT_DIR / image_file
        png_path.write_bytes(data)
        manifest = {
            "gate": "moss-sft-gate2_5",
            "fixture_id": fx["fixture_id"],
            "fixture_name": fx["fixture_name"],
            "status": "generated",
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
            "identity_summary": fx["identity_summary"],
            "outfit_tags": fx["outfit_tags"],
            "final_positive_prompt": attempt.payload.get("final_positive_prompt")
            or draft.rendered_base_positive,
            "human_score_total": None,
            "commit": commit,
            "asset_id": asset_id,
            "generation_attempt_id": rendered["generation_attempt_id"],
        }
        man_path = _ARTIFACT_DIR / f"{fx['fixture_id']}_{fx['slug']}.manifest.json"
        man_path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        # Integrity: file sha256 matches stored
        assert hashlib.sha256(data).hexdigest() == sha256

        results.append(
            {
                "fixture_id": fx["fixture_id"],
                "fixture_name": fx["fixture_name"],
                "seed": seed,
                "auto_status": "passed",
                "png_path": png_path,
                "short_notes": f"mean_luma={mean:.1f}",
            }
        )

    assert len(results) == 11
    sheet_path = _ARTIFACT_DIR / "contact_sheet.png"
    _build_contact_sheet(results, sheet_path)
    assert sheet_path.exists()
    assert sheet_path.stat().st_size > 10_000

    scores_path = _ARTIFACT_DIR / "human_scores.csv"
    _write_human_scores_csv(scores_path, results)
    summary_path = _ARTIFACT_DIR / "SUMMARY.md"
    _write_summary(
        summary_path,
        commit=commit,
        comfy_version=comfy_version,
        fixtures=results,
    )
    assert summary_path.exists()
    assert scores_path.exists()
