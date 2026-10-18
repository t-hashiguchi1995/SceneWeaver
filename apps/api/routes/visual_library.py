from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query

from apps.api.deps import container
from creator_studio.application.visual_library import VisualLibraryQuery
from creator_studio.infrastructure.container import Container

router = APIRouter(prefix="/api/v1", tags=["visual-library"])

SourceType = Literal["prompt_preset", "marketplace_item"]


@router.get("/visual-library")
def list_visual_library(
    q: str = Query(default=""),
    kind: str | None = None,
    content_rating: str | None = None,
    model: str | None = None,
    has_preview: bool | None = None,
    c: Container = Depends(container),
) -> list[dict[str, Any]]:
    return VisualLibraryQuery(c.uow()).list_items(
        q=q,
        kind=kind,
        content_rating=content_rating,
        model=model,
        has_preview=has_preview,
    )


@router.get("/visual-library/{source_type}/{source_id}")
def get_visual_library_item(
    source_type: SourceType,
    source_id: str,
    c: Container = Depends(container),
) -> dict[str, Any]:
    item = VisualLibraryQuery(c.uow()).get_item(source_type, source_id)
    if item is None:
        raise HTTPException(status_code=404, detail="visual library item not found")
    return item
