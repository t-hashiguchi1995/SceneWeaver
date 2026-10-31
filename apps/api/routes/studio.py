from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from apps.api.deps import container
from creator_studio.adapters.image.comfy_errors import ComfyError
from creator_studio.application.studio.scratch import ScratchStudioService
from creator_studio.infrastructure.container import Container

router = APIRouter(prefix="/api/v1/studio", tags=["studio"])


class CreateSessionBody(BaseModel):
    character_id: str = Field(min_length=1)
    outfit_profile_id: str | None = None
    capability: str = "BaseRender"


class ApplyPoseBody(BaseModel):
    pose_id: str
    pose_view: str = "front"
    flipped: bool = False
    control_strength: float = Field(default=1.0, ge=0.0, le=2.0)


class LifecycleBody(BaseModel):
    lifecycle: Literal["draft", "generated", "adopted", "abandoned"]


class MaterializeBody(BaseModel):
    project_id: str | None = None
    generation_attempt_id: str | None = None


class StudioRenderBody(BaseModel):
    seed: int | None = Field(default=None, ge=0, le=2147483647)


def _scratch(c: Container) -> ScratchStudioService:
    return ScratchStudioService(c)


@router.post("/sessions")
def create_session(body: CreateSessionBody, c: Container = Depends(container)) -> dict[str, Any]:
    try:
        return _scratch(c).create_session(
            character_id=body.character_id,
            outfit_profile_id=body.outfit_profile_id,
            capability=body.capability,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/sessions/{shot_id}")
def get_session(shot_id: str, c: Container = Depends(container)) -> dict[str, Any]:
    try:
        return _scratch(c).get_session(shot_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.post("/sessions/{shot_id}/pose")
def apply_pose(
    shot_id: str, body: ApplyPoseBody, c: Container = Depends(container)
) -> dict[str, Any]:
    try:
        return _scratch(c).apply_pose(
            shot_id,
            pose_id=body.pose_id,
            pose_view=body.pose_view,
            flipped=body.flipped,
            control_strength=body.control_strength,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/sessions/{shot_id}/render")
def render_session(
    shot_id: str, body: StudioRenderBody, c: Container = Depends(container)
) -> dict[str, Any]:
    try:
        shot = c.shot_pipeline().get_shot(shot_id)
        pose_uri = shot.render_spec.get("pose_asset_uri")
        use_pose = bool(pose_uri) or str(shot.render_spec.get("capability") or "") == (
            "PoseControlledRender"
        )
        result = c.shot_pipeline().render(
            shot_id,
            use_pose=use_pose,
            pose_asset_uri=str(pose_uri) if pose_uri else None,
            seed=body.seed,
        )
        _scratch(c).mark_generated(shot_id)
        session = _scratch(c).get_session(shot_id)
        return {**result, "session": session}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ComfyError as e:
        raise HTTPException(
            status_code=502,
            detail={"code": e.code.value, "message": str(e)},
        ) from e


@router.post("/sessions/{shot_id}/lifecycle")
def set_lifecycle(
    shot_id: str, body: LifecycleBody, c: Container = Depends(container)
) -> dict[str, Any]:
    try:
        return _scratch(c).set_lifecycle(shot_id, body.lifecycle)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/sessions/{shot_id}/abandon")
def abandon_session(shot_id: str, c: Container = Depends(container)) -> dict[str, Any]:
    try:
        return _scratch(c).abandon(shot_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/sessions/{shot_id}/materialize")
def materialize_session(
    shot_id: str, body: MaterializeBody, c: Container = Depends(container)
) -> dict[str, Any]:
    try:
        return _scratch(c).materialize_to_story(
            shot_id,
            project_id=body.project_id,
            generation_attempt_id=body.generation_attempt_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
