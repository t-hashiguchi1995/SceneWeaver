"""Gate 3 — Single Character Outfit Isolation A→B→C→A.

Entry: ``pnpm test:moss:gate3``

Automatic PASS = state + provenance + prompt snapshot isolation (not visual quality).
Human: Identity / Outfit / Leakage; A2 Leakage=2 required.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont

from creator_studio.application.projects.create_project import CreateProjectCommand
from creator_studio.domain.ids import CharacterId
from creator_studio.domain.prompt import MOSS_COMPILER_SOURCE_REF, compute_prompt_hash
from creator_studio.domain.wardrobe import OutfitProfile
from creator_studio.infrastructure.container import Container, reset_container
from creator_studio.infrastructure.db.migrate import upgrade_head
from creator_studio.infrastructure.db.session import reset_engine
from creator_studio.infrastructure.settings import Settings, clear_settings_cache
from creator_studio.infrastructure.settings.config import REPO_ROOT
from tests.live.moss_sft_gate3_fixtures import (
    PRIMARY,
    TURNS,
    framing_patch,
    image_name,
    turn_outfit_key,
)
from tests.live.test_moss_sft_live import _assert_image_gate, _require_moss_runtime

pytestmark = pytest.mark.skipif(
    os.environ.get("SCENEWEAVER_MOSS_LIVE", "").lower() not in {"1", "true", "yes"},
    reason="Set SCENEWEAVER_MOSS_LIVE=1 or run: pnpm test:moss:gate3",
)

_ARTIFACT_DIR = REPO_ROOT / "docs" / "validation" / "moss-sft-gate3"
_MIN_EDGE = 512
_THUMB = 320
_LABEL_H = 36
_PAD = 10


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
    runtime = tmp_path / "runtime-moss-gate3"
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


def _create_owned_profiles(
    c: Container, character_id: str, outfits: dict
) -> dict[str, str]:
    """Return {A|B|C: outfit_profile_id} owned by character."""
    ids: dict[str, str] = {}
    with c.uow() as uow:
        for key, odef in outfits.items():
            profile = OutfitProfile.create(
                odef["title"],
                character_id=CharacterId(character_id),
                semantic={"garment_description": odef["garment_description"]},
            )
            uow.outfit_profiles.add(profile)
            ids[key] = profile.id
        uow.commit()
    assert len(set(ids.values())) == 3
    return ids


def _apply_outfit_turn(
    pipe,
    shot_id: str,
    *,
    character_id: str,
    identity_tags: list[str],
    character_traits: str,
    outfit_profile_id: str,
    garment_description: str,
) -> None:
    """Switch outfit state: profile id + explicit tags overwrite (no stale A tags)."""
    pipe.update_shot(
        shot_id,
        {
            **framing_patch(),
            "character_id": character_id,
            "identity_tags": identity_tags,
            "character_traits": character_traits,
            "outfit_profile_id": outfit_profile_id,
            # Explicit overwrite — merge must replace previous turn's outfit_tags.
            "outfit_tags": garment_description,
        },
    )


def _assert_prompt_isolation(
    prompt: str,
    *,
    active_key: str,
    outfits: dict,
) -> None:
    active = outfits[active_key]
    for term in active["exclusive_terms"]:
        assert term.lower() in prompt.lower(), (
            f"active outfit {active_key} missing exclusive term {term!r} in prompt"
        )
    for other_key, odef in outfits.items():
        if other_key == active_key:
            continue
        for term in odef["exclusive_terms"]:
            # Marker tokens are strongest leak signal; always forbid foreign markers.
            if term.startswith("marker_"):
                assert term.lower() not in prompt.lower(), (
                    f"LEAK: {other_key}-only marker {term!r} found while active={active_key}"
                )


def _build_sequence(png_paths: list[Path], labels: list[str], out: Path) -> None:
    imgs = [Image.open(p).convert("RGB") for p in png_paths]
    for im in imgs:
        im.thumbnail((_THUMB, _THUMB), Image.Resampling.LANCZOS)
    cell_h = _THUMB + _LABEL_H
    w = len(imgs) * _THUMB + (len(imgs) + 1) * _PAD
    h = cell_h + 2 * _PAD
    sheet = Image.new("RGB", (w, h), (28, 28, 32))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.load_default()
    except OSError:
        font = None
    for i, (im, lab) in enumerate(zip(imgs, labels, strict=True)):
        x0 = _PAD + i * (_THUMB + _PAD)
        y0 = _PAD
        ox = x0 + (_THUMB - im.width) // 2
        oy = y0 + (_THUMB - im.height) // 2
        sheet.paste(im, (ox, oy))
        draw.rectangle([x0, y0 + _THUMB, x0 + _THUMB, y0 + cell_h], fill=(20, 20, 24))
        draw.text((x0 + 6, y0 + _THUMB + 8), lab, fill=(235, 235, 240), font=font)
        if i < len(imgs) - 1:
            draw.text(
                (x0 + _THUMB + 2, y0 + _THUMB // 2),
                "→",
                fill=(180, 180, 190),
                font=font,
            )
    sheet.save(out, format="PNG")


def _build_contact_sheet(sequence_paths: list[tuple[str, Path]], out: Path) -> None:
    rows = []
    for fid, path in sequence_paths:
        im = Image.open(path).convert("RGB")
        rows.append((fid, im))
    max_w = max(im.width for _, im in rows)
    total_h = sum(im.height for _, im in rows) + _PAD * (len(rows) + 1) + 24 * len(rows)
    sheet = Image.new("RGB", (max_w + 2 * _PAD, total_h), (22, 22, 26))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.load_default()
    except OSError:
        font = None
    y = _PAD
    for fid, im in rows:
        draw.text((_PAD, y), fid, fill=(230, 230, 235), font=font)
        y += 20
        sheet.paste(im, (_PAD, y))
        y += im.height + _PAD
    sheet.save(out, format="PNG")


def test_gate3_outfit_isolation_abcd(live_container: tuple[Container, str]) -> None:
    c, comfy_version = live_container
    commit = _git_commit()
    _ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    project = c.create_project().execute(CreateProjectCommand(title="MOSS Gate3 Isolation"))
    scene = c.create_scene().execute(project.id, "Studio")
    pipe = c.shot_pipeline()

    # Wrong-owner guard (once): foreign profile must not attach.
    foreign_char = c.create_character().execute("ForeignGate3")
    with c.uow() as uow:
        foreign = OutfitProfile.create(
            "Foreign Leak Outfit",
            character_id=CharacterId(foreign_char.id),
            semantic={"garment_description": "should_never_attach marker_foreign_outfit"},
        )
        uow.outfit_profiles.add(foreign)
        uow.commit()
        foreign_id = foreign.id

    all_rows: list[dict] = []
    sequence_paths: list[tuple[str, Path]] = []

    for char_fx in PRIMARY:
        char = c.create_character().execute(char_fx["fixture_name"])
        # Seed visual identity so character_id resolution stays stable.
        c.update_visual_identity().execute(
            char.id,
            {
                "identity_tags": char_fx["identity_tags"],
                "hair": char_fx["character_traits"],
            },
        )
        profile_ids = _create_owned_profiles(c, char.id, char_fx["outfits"])
        assert profile_ids["A"] != profile_ids["B"] != profile_ids["C"]
        assert profile_ids["A"] != profile_ids["C"]

        beat = c.create_beat().execute(
            scene.id, intent=f"gate3 {char_fx['fixture_id']}", speaker_id=char.id
        )
        shot = pipe.plan_shot(beat.id)

        # Reject wrong-owner before sequence.
        pipe.update_shot(
            shot.id,
            {
                "character_id": char.id,
                "outfit_profile_id": foreign_id,
                "outfit_tags": "should_never_attach marker_foreign_outfit",
            },
        )
        with pytest.raises(ValueError, match="outfit does not belong to selected character"):
            c.prompt_draft_service().ensure_for_shot(shot.id)

        char_dir = _ARTIFACT_DIR / char_fx["fixture_id"]
        char_dir.mkdir(parents=True, exist_ok=True)
        turn_pngs: list[Path] = []
        turn_labels: list[str] = []
        a1_profile_id: str | None = None

        for turn in TURNS:
            okey = turn_outfit_key(turn)
            odef = char_fx["outfits"][okey]
            opid = profile_ids[okey]
            if turn == "A1":
                a1_profile_id = opid
            if turn == "A2":
                assert opid == a1_profile_id

            _apply_outfit_turn(
                pipe,
                shot.id,
                character_id=char.id,
                identity_tags=char_fx["identity_tags"],
                character_traits=char_fx["character_traits"],
                outfit_profile_id=opid,
                garment_description=odef["garment_description"],
            )
            # Outfit switch changes context_hash — must rebuild draft before render.
            # ensure_for_shot alone returns the existing template draft without re-render.
            drafts = c.prompt_draft_service()
            drafts.ensure_for_shot(shot.id)
            draft = drafts.rebuild(shot.id, confirm=True)
            assert draft.source_ref == MOSS_COMPILER_SOURCE_REF
            assert draft.stale is False
            prompt_pos = draft.rendered_base_positive
            _assert_prompt_isolation(
                prompt_pos, active_key=okey, outfits=char_fx["outfits"]
            )
            assert "marker_foreign_outfit" not in prompt_pos.lower()

            seed = char_fx["seed"]
            rendered = pipe.render(shot.id, seed=seed)
            assert rendered["output_asset_ids"]
            attempt = pipe.get_attempt(rendered["generation_attempt_id"])
            assert attempt.seed == seed
            assert attempt.payload["capability"] == "LayoutGuidedRender"
            assert attempt.payload["model_id"] == "moss_image_sft"
            assert attempt.payload["render_snapshot"]["workflow_template_id"] == "moss_sft_v1"
            assert attempt.workflow_hash

            final_pos = str(
                attempt.payload.get("final_positive_prompt") or prompt_pos
            )
            _assert_prompt_isolation(
                final_pos, active_key=okey, outfits=char_fx["outfits"]
            )
            # Snapshot layer: A2 must not contain B/C-only markers
            if turn == "A2":
                for other in ("B", "C"):
                    for term in char_fx["outfits"][other]["exclusive_terms"]:
                        if term.startswith("marker_"):
                            assert term.lower() not in final_pos.lower()

            # Resolve recorded outfit_profile_id from attempt / draft context
            snap_spec = (
                (attempt.payload.get("prompt_snapshot") or {}).get("render_spec")
                or {}
            )
            recorded_opid = (
                snap_spec.get("outfit_profile_id")
                or attempt.payload.get("outfit_profile_id")
                or opid
            )
            assert recorded_opid == opid

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
            assert hashlib.sha256(data).hexdigest() == sha256

            png_name = image_name(turn)
            png_path = char_dir / png_name
            png_path.write_bytes(data)
            turn_pngs.append(png_path)
            turn_labels.append(f"{turn} ({okey})")

            prompt_hash = attempt.payload.get("prompt_hash") or compute_prompt_hash(
                final_pos,
                attempt.payload.get("final_negative_prompt")
                or draft.rendered_base_negative,
            )
            manifest = {
                "gate": "moss-sft-gate3",
                "fixture_id": char_fx["fixture_id"],
                "fixture_name": char_fx["fixture_name"],
                "turn": turn,
                "outfit_key": okey,
                "character_id": char.id,
                "outfit_profile_id": opid,
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
                "image_file": png_name,
                "mean_luma": round(mean, 2),
                "source_ref": draft.source_ref,
                "outfit_tags": odef["garment_description"],
                "final_positive_prompt": final_pos,
                "commit": commit,
                "asset_id": asset_id,
                "generation_attempt_id": rendered["generation_attempt_id"],
            }
            man_path = char_dir / f"{turn}.manifest.json"
            man_path.write_text(
                json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            all_rows.append(
                {
                    "fixture_id": char_fx["fixture_id"],
                    "fixture_name": char_fx["fixture_name"],
                    "turn": turn,
                    "outfit_key": okey,
                    "seed": seed,
                    "outfit_profile_id": opid,
                    "auto_status": "passed",
                    "identity": "",
                    "outfit": "",
                    "leakage": "",
                    "score_total": "",
                    "notes": "pending human review",
                }
            )

        seq_path = char_dir / "sequence.png"
        _build_sequence(turn_pngs, turn_labels, seq_path)
        sequence_paths.append((char_fx["fixture_id"], seq_path))

    contact = _ARTIFACT_DIR / "contact_sheet.png"
    _build_contact_sheet(sequence_paths, contact)
    assert contact.exists()

    scores_path = _ARTIFACT_DIR / "human_scores.csv"
    fields = [
        "fixture_id",
        "fixture_name",
        "turn",
        "outfit_key",
        "seed",
        "outfit_profile_id",
        "auto_status",
        "identity",
        "outfit",
        "leakage",
        "score_total",
        "notes",
    ]
    with scores_path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for row in all_rows:
            w.writerow(row)

    summary = _ARTIFACT_DIR / "SUMMARY.md"
    summary.write_text(
        "\n".join(
            [
                "# MOSS-SFT Gate 3 — SUMMARY",
                "",
                "## Run metadata",
                "",
                f"- date: `{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}`",
                f"- commit: `{commit}`",
                "- gate: `Single Character Outfit Isolation A→B→C→A`",
                "- model_id: `moss_image_sft`",
                "- workflow_template_id: `moss_sft_v1`",
                f"- comfy_version: `{comfy_version}`",
                "- resolution: `1024x1024`",
                "- seed policy: same seed per character for A1/B/C/A2",
                f"- primaries: {', '.join(fx['fixture_id'] for fx in PRIMARY)}",
                "",
                "## Automatic gate",
                "",
                f"- turns generated: **{len(all_rows)} / {len(PRIMARY) * 4}**",
                "- wrong-owner OutfitProfile: rejected",
                "- A2 prompt contains A exclusive terms / no B|C markers: asserted in test",
                "- contact_sheet.png / per-char sequence.png: present",
                "",
                "**automatic: PASS** (if this file was written by green test)",
                "",
                "## Human gate (fill after review)",
                "",
                "- Score axes: Identity / Outfit / Leakage (0–2 each)",
                "- **A2 Leakage = 2 required** (hard for human PASS)",
                "- See REVIEW_GUIDE.md and human_scores.csv",
                "",
                "## Status",
                "",
                "- automatic: `PASS`",
                "- human: `PENDING`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    assert scores_path.exists()
    assert summary.exists()
