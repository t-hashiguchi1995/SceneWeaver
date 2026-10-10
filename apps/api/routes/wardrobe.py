from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from apps.api.deps import container
from creator_studio.adapters.image.comfy_errors import ComfyError
from creator_studio.infrastructure.container import Container

router = APIRouter(prefix="/api/v1", tags=["wardrobe"])


class TryOnCreate(BaseModel):
    character_id: str
    marketplace_item_id: str
    source_asset_id: str | None = None
    scene_id: str | None = None


class TryOnAdopt(BaseModel):
    asset_id: str
    scene_id: str | None = None


@router.get("/market/items")
def search_market(
    q: str = Query(default=""),
    category: str | None = None,
    c: Container = Depends(container),
) -> list[dict[str, Any]]:
    return c.search_market().execute(q, category=category)


@router.post("/tryon/sessions")
def create_tryon(body: TryOnCreate, c: Container = Depends(container)) -> dict[str, Any]:
    try:
        result = c.run_tryon().execute(
            character_id=body.character_id,
            marketplace_item_id=body.marketplace_item_id,
            source_asset_id=body.source_asset_id,
            scene_id=body.scene_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ComfyError as e:
        raise HTTPException(
            status_code=502,
            detail={"code": e.code.value, "message": str(e)},
        ) from e
    return result.__dict__


@router.post("/tryon/sessions/{session_id}/adopt")
def adopt_tryon(
    session_id: str,
    body: TryOnAdopt,
    c: Container = Depends(container),
) -> dict[str, Any]:
    try:
        return c.adopt_tryon().execute(session_id, body.asset_id, scene_id=body.scene_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e