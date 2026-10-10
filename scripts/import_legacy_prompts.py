#!/usr/bin/env python3
"""Import legacy prompt YAML into SceneWeaver Prompt Library / Character seeds.

Boundary (ADR 0010 / 0011):
  - This script normalizes and stores PromptPreset / Character / Marketplace seeds.
  - It does NOT assemble runtime Default Prompt strings or PromptDraft.rendered_base.
  - Default Prompt Builder (Sprint 4) consumes the library + ResolvedPromptContext.

Usage:
  uv run python scripts/import_legacy_prompts.py --source /path/to/prompts --dry-run
  uv run python scripts/import_legacy_prompts.py --source /path/to/prompts.zip --apply
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import zipfile
from collections import Counter
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Iterator

import yaml

# Ensure repo src is importable when run as script
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from creator_studio.domain.character import Character, VisualIdentity  # noqa: E402
from creator_studio.domain.ids import new_id  # noqa: E402
from creator_studio.domain.timeutil import utc_now  # noqa: E402
from creator_studio.domain.wardrobe import MarketplaceItem  # noqa: E402
from creator_studio.infrastructure.container import Container  # noqa: E402
from creator_studio.infrastructure.db.migrate import upgrade_head  # noqa: E402
from creator_studio.infrastructure.db.models.prompt import (  # noqa: E402
    LegacyImportRecordRow,
    PromptPresetRow,
)
from creator_studio.infrastructure.settings import get_settings  # noqa: E402

SOURCE = "legacy_prompt_library"


@dataclass
class PlannedRow:
    status: str
    entity_type: str
    source_file: str
    legacy_key: str
    label: str
    detail: str = ""
    content_hash: str = ""
    payload: dict[str, Any] = field(default_factory=dict)


def content_hash(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def canonical_source_file(rel: str) -> str:
    """ADR 0010: POSIX path relative to import root — never host absolute paths."""
    normalized = rel.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    if (
        not normalized
        or normalized.startswith("/")
        or Path(normalized).is_absolute()
        or (len(normalized) >= 2 and normalized[1] == ":" and normalized[0].isalpha())
    ):
        raise ValueError(f"source_file must be relative to import root, got: {rel!r}")
    return normalized


def classify_path(rel: str, data: dict[str, Any] | None = None) -> str:
    name = Path(rel).name.lower()
    if "r18" in name or name.startswith("presets_r18"):
        return "adult-tagged"
    if data and data.get("r18") is True:
        return "adult-tagged"
    if name.startswith("sfw_") or "category_labels" in name or name in {
        "costumes_shared.yaml",
        "lighting_default.yaml",
        "stand_seiso_uniform.yaml",
    }:
        return "sfw"
    if rel.startswith("characters/") and "r18" not in name:
        # Character packs may still pull r18 includes — mark review if includes r18
        includes = ((data or {}).get("prompt") or {}).get("includes") or []
        if any("r18" in str(x).lower() for x in includes):
            return "review-required"
        return "sfw"
    return "unsupported"


def iter_source_files(source: Path) -> Iterator[tuple[str, Path]]:
    if source.is_file() and source.suffix == ".zip":
        extract = REPO_ROOT / "legacy" / "_extracted"
        if extract.exists():
            shutil.rmtree(extract)
        extract.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(source) as zf:
            zf.extractall(extract)
        root = extract / "prompts" if (extract / "prompts").exists() else extract
        source = root
    if not source.is_dir():
        raise SystemExit(f"source not found: {source}")
    for path in sorted(source.rglob("*.yaml")):
        rel = canonical_source_file(str(path.relative_to(source)))
        yield rel, path


def plan_character(rel: str, data: dict[str, Any]) -> list[PlannedRow]:
    rating = classify_path(rel, data)
    if rating != "sfw":
        return [
            PlannedRow(
                status=rating if rating != "review-required" else "unsupported",
                entity_type="character",
                source_file=rel,
                legacy_key=Path(rel).stem,
                label=str(data.get("name") or Path(rel).stem),
                detail=rating,
            )
        ]
    prompt = data.get("prompt") or {}
    payload = {
        "display_name": data.get("name") or Path(rel).stem,
        "identity": prompt.get("identity") or "",
        "base": prompt.get("base") or "",
        "categories": prompt.get("categories") or {},
    }
    return [
        PlannedRow(
            status="create",
            entity_type="character",
            source_file=rel,
            legacy_key=Path(rel).stem,
            label=str(payload["display_name"]),
            content_hash=content_hash(payload),
            payload=payload,
        )
    ]


def plan_labels(rel: str, data: dict[str, Any]) -> list[PlannedRow]:
    labels = data.get("labels") or {}
    rows: list[PlannedRow] = []
    for key, ja in labels.items():
        if not ja:
            rows.append(
                PlannedRow(
                    status="missing-label",
                    entity_type="category_label",
                    source_file=rel,
                    legacy_key=str(key),
                    label=str(key),
                )
            )
            continue
        payload = {"category": key, "label_ja": ja}
        rows.append(
            PlannedRow(
                status="create",
                entity_type="category_label",
                source_file=rel,
                legacy_key=str(key),
                label=str(ja),
                content_hash=content_hash(payload),
                payload=payload,
            )
        )
    return rows


def plan_dynamic_sfw(rel: str, data: dict[str, Any]) -> list[PlannedRow]:
    rating = classify_path(rel, data)
    if rating != "sfw":
        return [
            PlannedRow(
                status="adult-tagged" if rating == "adult-tagged" else "unsupported",
                entity_type="prompt_preset",
                source_file=rel,
                legacy_key=Path(rel).stem,
                label=Path(rel).stem,
                detail=rating,
            )
        ]
    rows: list[PlannedRow] = []
    categories = data.get("categories") or data
    if not isinstance(categories, dict):
        return [
            PlannedRow(
                status="invalid-prompt",
                entity_type="prompt_preset",
                source_file=rel,
                legacy_key=Path(rel).stem,
                label=Path(rel).stem,
            )
        ]
    for cat, items in categories.items():
        if cat in {"name", "prompt", "labels"}:
            continue
        if not isinstance(items, list):
            continue
        for idx, item in enumerate(items):
            if isinstance(item, dict) and item.get("r18") is True:
                rows.append(
                    PlannedRow(
                        status="adult-tagged",
                        entity_type="prompt_preset",
                        source_file=rel,
                        legacy_key=f"{cat}:{item.get('name') or idx}",
                        label=str(item.get("name") or idx),
                    )
                )
                continue
            if isinstance(item, str):
                fragment = item
                key = f"{cat}:{idx}"
                label = f"{cat}-{idx}"
            elif isinstance(item, dict):
                fragment = str(item.get("prompt") or "")
                key = f"{cat}:{item.get('name') or idx}"
                label = str(item.get("name") or key)
            else:
                rows.append(
                    PlannedRow(
                        status="invalid-prompt",
                        entity_type="prompt_preset",
                        source_file=rel,
                        legacy_key=f"{cat}:{idx}",
                        label=str(idx),
                    )
                )
                continue
            if not fragment.strip():
                rows.append(
                    PlannedRow(
                        status="invalid-prompt",
                        entity_type="prompt_preset",
                        source_file=rel,
                        legacy_key=key,
                        label=label,
                    )
                )
                continue
            payload = {
                "kind": "snippet",
                "category": cat,
                "label": label,
                "prompt_fragment": fragment,
                "content_rating": "general",
            }
            rows.append(
                PlannedRow(
                    status="create",
                    entity_type="prompt_preset",
                    source_file=rel,
                    legacy_key=key,
                    label=label,
                    content_hash=content_hash(payload),
                    payload=payload,
                )
            )
    return rows


def plan_stand_seiso(rel: str, data: dict[str, Any]) -> list[PlannedRow]:
    rows: list[PlannedRow] = []
    # outfits
    for section, kind in (
        ("outfits", "outfit"),
        ("shoes", "shoes"),
        ("accessories", "accessory"),
        ("poses", "pose"),
    ):
        items = data.get(section) or []
        if isinstance(items, dict):
            items = [{"name": k, **(v if isinstance(v, dict) else {"prompt": v})} for k, v in items.items()]
        if not isinstance(items, list):
            continue
        for idx, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            if item.get("r18") is True:
                rows.append(
                    PlannedRow(
                        status="adult-tagged",
                        entity_type="marketplace_item" if kind == "outfit" else "prompt_preset",
                        source_file=rel,
                        legacy_key=f"{section}:{item.get('name') or item.get('label') or idx}",
                        label=str(item.get("label") or item.get("name") or idx),
                    )
                )
                continue
            label = str(item.get("label") or item.get("name") or f"{section}-{idx}")
            fragment = str(item.get("prompt") or item.get("character_outfit") or "")
            if not fragment.strip():
                rows.append(
                    PlannedRow(
                        status="invalid-prompt",
                        entity_type="prompt_preset",
                        source_file=rel,
                        legacy_key=f"{section}:{label}",
                        label=label,
                    )
                )
                continue
            if kind == "outfit":
                payload = {
                    "title": label,
                    "category": "costume",
                    "garment_description": fragment,
                    "content_rating": "general",
                }
                rows.append(
                    PlannedRow(
                        status="create",
                        entity_type="marketplace_item",
                        source_file=rel,
                        legacy_key=f"outfit:{label}",
                        label=label,
                        content_hash=content_hash(payload),
                        payload=payload,
                    )
                )
            else:
                payload = {
                    "kind": kind,
                    "category": kind,
                    "label": label,
                    "prompt_fragment": fragment,
                    "content_rating": "general",
                }
                rows.append(
                    PlannedRow(
                        status="create",
                        entity_type="prompt_preset",
                        source_file=rel,
                        legacy_key=f"{section}:{label}",
                        label=label,
                        content_hash=content_hash(payload),
                        payload=payload,
                    )
                )

    expressions = data.get("expressions") or {}
    if isinstance(expressions, dict):
        for key, val in expressions.items():
            entry = val if isinstance(val, dict) else {"prompt": val}
            if entry.get("r18") is True:
                rows.append(
                    PlannedRow(
                        status="adult-tagged",
                        entity_type="prompt_preset",
                        source_file=rel,
                        legacy_key=f"expression:{key}",
                        label=str(key),
                    )
                )
                continue
            fragment = str(entry.get("prompt") or "")
            if not fragment.strip():
                rows.append(
                    PlannedRow(
                        status="invalid-prompt",
                        entity_type="prompt_preset",
                        source_file=rel,
                        legacy_key=f"expression:{key}",
                        label=str(key),
                    )
                )
                continue
            payload = {
                "kind": "expression",
                "category": "expression",
                "label": key,
                "prompt_fragment": fragment,
                "content_rating": "general",
            }
            rows.append(
                PlannedRow(
                    status="create",
                    entity_type="prompt_preset",
                    source_file=rel,
                    legacy_key=f"expression:{key}",
                    label=str(key),
                    content_hash=content_hash(payload),
                    payload=payload,
                )
            )
    return rows


def build_plan(source: Path) -> list[PlannedRow]:
    planned: list[PlannedRow] = []
    for rel, path in iter_source_files(source):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except Exception as exc:  # noqa: BLE001
            planned.append(
                PlannedRow(
                    status="invalid-prompt",
                    entity_type="file",
                    source_file=rel,
                    legacy_key=Path(rel).stem,
                    label=rel,
                    detail=str(exc),
                )
            )
            continue
        if not isinstance(data, dict):
            planned.append(
                PlannedRow(
                    status="unsupported",
                    entity_type="file",
                    source_file=rel,
                    legacy_key=Path(rel).stem,
                    label=rel,
                )
            )
            continue
        if rel.startswith("characters/") or "/characters/" in rel:
            planned.extend(plan_character(rel, data))
        elif "category_labels_ja" in rel:
            planned.extend(plan_labels(rel, data))
        elif "stand_seiso_uniform" in rel:
            planned.extend(plan_stand_seiso(rel, data))
        elif rel.startswith("dynamic/") or "/dynamic/" in rel:
            planned.extend(plan_dynamic_sfw(rel, data))
        else:
            planned.append(
                PlannedRow(
                    status="unsupported",
                    entity_type="file",
                    source_file=rel,
                    legacy_key=Path(rel).stem,
                    label=rel,
                )
            )
    return planned


def reconcile_idempotency(planned: list[PlannedRow], container: Container) -> list[PlannedRow]:
    out: list[PlannedRow] = []
    with container.uow() as uow:
        for row in planned:
            if row.status != "create":
                out.append(row)
                continue
            existing = uow.legacy_imports.get(SOURCE, row.source_file, row.legacy_key)
            if existing is None:
                out.append(row)
                continue
            if existing.content_hash == row.content_hash:
                out.append(replace(row, status="unchanged"))
            else:
                out.append(
                    replace(
                        row,
                        status="conflict",
                        detail="content differs from imported record",
                    )
                )
    return out


def apply_plan(planned: list[PlannedRow], container: Container) -> Counter[str]:
    counts: Counter[str] = Counter()
    with container.uow() as uow:
        for row in planned:
            if row.status != "create":
                counts[row.status] += 1
                continue
            entity_id = new_id()
            now = utc_now()
            if row.entity_type == "character":
                character = Character.create(str(row.payload["display_name"]))
                identity_text = str(row.payload.get("identity") or "")
                tags = [t.strip() for t in identity_text.replace("\n", ",").split(",") if t.strip()]
                character.visual_identity = VisualIdentity(identity_tags=tags[:32])
                uow.characters.add(character)
                entity_id = str(character.id)
            elif row.entity_type == "marketplace_item":
                item = MarketplaceItem.create(
                    title=str(row.payload["title"]),
                    category=str(row.payload.get("category") or "costume"),
                    region="jp",
                    garment_description=str(row.payload.get("garment_description") or ""),
                    source={"library": SOURCE, "file": row.source_file, "key": row.legacy_key},
                )
                uow.marketplace.add(item)
                entity_id = item.id
            elif row.entity_type in {"prompt_preset", "category_label"}:
                preset = PromptPresetRow(
                    id=entity_id,
                    kind=str(row.payload.get("kind") or row.entity_type),
                    label=row.label,
                    prompt_fragment=str(
                        row.payload.get("prompt_fragment") or row.payload.get("label_ja") or ""
                    ),
                    category=str(row.payload.get("category") or "") or None,
                    content_rating=str(row.payload.get("content_rating") or "general"),
                    enabled=True,
                    payload_json=row.payload,
                    source=SOURCE,
                    source_file=row.source_file,
                    legacy_key=row.legacy_key,
                    content_hash=row.content_hash,
                    created_at=now,
                    updated_at=now,
                )
                uow.prompt_presets.add_row(preset)
            else:
                counts["unsupported"] += 1
                continue
            uow.legacy_imports.add(
                LegacyImportRecordRow(
                    id=new_id(),
                    source=SOURCE,
                    source_file=row.source_file,
                    legacy_key=row.legacy_key,
                    entity_type=row.entity_type,
                    entity_id=entity_id,
                    content_hash=row.content_hash,
                    created_at=now,
                )
            )
            counts["create"] += 1
        uow.commit()
    return counts


def print_report(planned: list[PlannedRow]) -> None:
    counts = Counter(r.status for r in planned)
    print("=== Legacy Prompt Import Report ===")
    for key in sorted(counts):
        print(f"  {key}: {counts[key]}")
    print("--- samples ---")
    by_status: dict[str, list[PlannedRow]] = {}
    for row in planned:
        by_status.setdefault(row.status, []).append(row)
    for status, rows in sorted(by_status.items()):
        sample = rows[:3]
        for s in sample:
            print(f"  [{status}] {s.entity_type} {s.source_file}::{s.legacy_key} ({s.label})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Import legacy SceneWeaver prompt YAML")
    parser.add_argument("--source", required=True, help="Directory or prompts.zip")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if args.dry_run == args.apply:
        raise SystemExit("specify exactly one of --dry-run or --apply")

    source = Path(args.source)
    settings = get_settings()
    upgrade_head(settings.sqlalchemy_url())
    container = Container(settings)

    planned = build_plan(source)
    planned = reconcile_idempotency(planned, container)
    print_report(planned)

    if args.apply:
        counts = apply_plan(planned, container)
        print("=== applied ===")
        for key in sorted(counts):
            print(f"  {key}: {counts[key]}")


if __name__ == "__main__":
    main()
