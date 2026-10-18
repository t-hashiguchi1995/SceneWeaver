from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from apps.api.deps import container
from creator_studio.application.e2e.seed import E2ESeedService, reset_runtime
from creator_studio.infrastructure.container import Container, reset_container
from creator_studio.infrastructure.db.migrate import upgrade_head
from creator_studio.infrastructure.db.session import reset_engine
from creator_studio.infrastructure.settings import clear_settings_cache, get_settings

router = APIRouter(prefix="/api/test", tags=["test-control"])


class SeedBody(BaseModel):
    scenario: str = Field(
        description=(
            "m1_foundation | m2_story | m3_tryon | m4_visual | m5_delivery | "
            "vertical_slice | visual_library"
        )
    )


def _require_test_control() -> None:
    settings = get_settings()
    if not settings.allows_test_control:
        raise HTTPException(status_code=404, detail="not found")


@router.post("/reset")
def reset_state(c: Container = Depends(container)) -> dict[str, str]:
    _require_test_control()
    settings = get_settings()
    reset_runtime(settings.runtime_path(), database_url=settings.sqlalchemy_url())
    reset_container()
    reset_engine()
    clear_settings_cache()
    fresh = get_settings()
    upgrade_head(fresh.sqlalchemy_url())
    reset_engine()
    reset_container()
    return {"status": "reset", "runtime": str(fresh.runtime_path())}


@router.post("/seed")
def seed(body: SeedBody, c: Container = Depends(container)) -> dict[str, Any]:
    _require_test_control()
    service = E2ESeedService(
        c.uow(),
        c.store_asset(),
        c.create_project(),
        c.create_character(),
        c.update_persona(),
        c.update_visual_identity(),
        c.create_scene(),
        c.create_beat(),
        c.seed_marketplace_item(),
    )
    try:
        result = service.seed(body.scenario)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {
        "scenario": result.scenario,
        "project_id": result.project_id,
        "character_id": result.character_id,
        "scene_id": result.scene_id,
        "beat_id": result.beat_id,
        "marketplace_item_id": result.marketplace_item_id,
        "tryon_base_asset_id": result.tryon_base_asset_id,
        "extras": result.extras or {},
    }


@router.post("/reload")
def reload_container(c: Container = Depends(container)) -> dict[str, str]:
    """Simulate process restart: drop in-memory container/engine, keep DB files."""
    _require_test_control()
    reset_container()
    reset_engine()
    clear_settings_cache()
    fresh = get_settings()
    # Warm a new container against the same SQLite file
    from creator_studio.infrastructure.container import get_container

    get_container()
    return {"status": "reloaded", "runtime": str(fresh.runtime_path())}


@router.get("/state")
def get_state(c: Container = Depends(container)) -> dict[str, Any]:
    _require_test_control()
    settings = get_settings()
    projects = c.list_projects().execute()
    jobs = c.list_jobs().execute(limit=50)
    characters = c.list_characters().execute()
    market = c.search_market().execute()

    shots: list[dict[str, Any]] = []
    attempts: list[dict[str, Any]] = []
    adopted_assets: list[dict[str, Any]] = []
    with c.uow() as uow:
        from sqlalchemy import select

        from creator_studio.infrastructure.db.models.asset import AssetRow
        from creator_studio.infrastructure.db.models.shot import (
            GenerationAttemptRow,
            ShotRow,
        )

        for row in uow.session.scalars(select(ShotRow)).all():  # type: ignore[union-attr]
            shots.append(
                {
                    "id": row.id,
                    "beat_id": row.beat_id,
                    "revision": row.revision,
                    "stale_reason": row.stale_reason,
                }
            )
        for row in uow.session.scalars(select(GenerationAttemptRow)).all():  # type: ignore[union-attr]
            attempts.append(
                {
                    "id": row.id,
                    "status": row.status,
                    "based_on_shot_revision": row.based_on_shot_revision,
                    "workflow_hash": row.workflow_hash,
                    "output_asset_ids": list(row.output_asset_ids_json or []),
                    "payload": dict(row.payload_json or {}),
                }
            )
        for row in uow.session.scalars(select(AssetRow)).all():  # type: ignore[union-attr]
            meta = dict(row.metadata_json or {})
            if meta.get("review_decision") == "adopted" or row.kind == "adopted":
                adopted_assets.append(
                    {"id": row.id, "sha256": row.sha256, "kind": row.kind}
                )

    runtime = settings.runtime_path()
    handoff_roots = list((runtime / "projects").glob("*/csp_handoff/r*")) if (
        runtime / "projects"
    ).exists() else []
    handoffs = []
    for root in handoff_roots:
        if not root.is_dir() or root.name.startswith("."):
            continue
        panel = root / "pages" / "page_001" / "panel_01_clean.png"
        manifest = root / "project_manifest.json"
        handoffs.append(
            {
                "revision": root.name,
                "path": str(root),
                "panel_exists": panel.exists(),
                "manifest_exists": manifest.exists(),
                "panel_path": str(panel) if panel.exists() else None,
            }
        )

    return {
        "environment": settings.environment,
        "runtime_dir": str(runtime),
        "project_count": len(projects),
        "job_count": len(jobs),
        "character_count": len(characters),
        "market_item_count": len(market),
        "shot_count": len(shots),
        "generation_attempt_count": len(attempts),
        "adopted_asset_count": len(adopted_assets),
        "handoff_count": len(handoffs),
        "projects": [p.__dict__ for p in projects[:20]],
        "jobs": [j.__dict__ for j in jobs[:20]],
        "shots": shots[:20],
        "generation_attempts": attempts[:20],
        "adopted_assets": adopted_assets[:20],
        "handoffs": handoffs[:20],
        "market": market[:20],
    }
