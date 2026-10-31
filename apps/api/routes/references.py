from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from apps.api.deps import container
from creator_studio.infrastructure.container import Container

router = APIRouter(prefix="/api/v1/references", tags=["references"])


@router.get("/poses")
def list_poses(c: Container = Depends(container)) -> list[dict[str, Any]]:
    return c.reference_pose_service().list_summaries()


@router.get("/poses/{pose_id}")
def get_pose(pose_id: str, c: Container = Depends(container)) -> dict[str, Any]:
    detail = c.reference_pose_service().get_detail(pose_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="pose not found")
    return detail


@router.get("/assets/{asset_path:path}")
def get_reference_asset(asset_path: str, c: Container = Depends(container)) -> Response:
    resolved = c.reference_pose_service().resolve_asset_bytes(asset_path)
    if resolved is None:
        raise HTTPException(status_code=404, detail="asset not found")
    data, mime = resolved
    return Response(
        content=data,
        media_type=mime,
        headers={"Cache-Control": "public, max-age=86400"},
    )
