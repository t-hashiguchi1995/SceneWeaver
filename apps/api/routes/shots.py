from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from apps.api.deps import container
from creator_studio.adapters.image.comfy_errors import ComfyError
from creator_studio.infrastructure.container import Container

router = APIRouter(prefix="/api/v1", tags=["shots"])


class RenderBody(BaseModel):
    use_pose: bool = False
    pose_asset_uri: str | None = None


@router.post("/beats/{beat_id}/shots/plan")
def plan_shot(beat_id: str, c: Container = Depends(container)) -> dict[str, Any]:
    try:
        return c.shot_pipeline().plan_shot(beat_id).__dict__
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.put("/shots/{shot_id}")
def update_shot(shot_id: str, body: dict[str, Any], c: Container = Depends(container)) -> dict[str, Any]:
    try:
        return c.shot_pipeline().update_shot(shot_id, body).__dict__
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/shots/{shot_id}/render")
def render_shot(shot_id: str, body: RenderBody, c: Container = Depends(container)) -> dict[str, Any]:
    try:
        return c.shot_pipeline().render(
            shot_id, use_pose=body.use_pose, pose_asset_uri=body.pose_asset_uri
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ComfyError as e:
        raise HTTPException(
            status_code=502,
            detail={"code": e.code.value, "message": str(e)},
        ) from e