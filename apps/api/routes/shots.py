from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from apps.api.deps import container
from creator_studio.adapters.image.comfy_errors import ComfyError
from creator_studio.application.camera.lock_service import CameraLockRequest
from creator_studio.domain.camera.errors import CameraLockError, http_status_for_camera_code
from creator_studio.infrastructure.container import Container

router = APIRouter(prefix="/api/v1", tags=["shots"])


@router.get('/prompt-library')
def prompt_library(c: Container = Depends(container)) -> list[dict[str, Any]]:
    with c.uow() as uow:
        return [{'id': p.id, 'label': p.label, 'category': p.category,
                 'prompt_fragment': p.prompt_fragment, 'content_rating': p.content_rating,
                 'source_file': p.source_file, 'version': p.content_hash}
                for p in uow.prompt_presets.list_enabled()]


class CameraLockBody(BaseModel):
    enabled: bool = False
    rig_id: str | None = None
    expected_rig_revision: int | None = None
    strategy: str | None = None
    pose_asset_id: str | None = None
    edit_mask_asset_id: str | None = None


class RenderBody(BaseModel):
    camera_lock: CameraLockBody | None = None
    source_attempt_id: str | None = None
    seed: int | None = Field(default=None, ge=0, le=2147483647)
    use_pose: bool = False
    pose_asset_uri: str | None = None


class PromptDraftEditBody(BaseModel):
    edited_positive: str = Field(min_length=0)
    edited_negative: str = Field(min_length=0)


class PromptDraftRebuildBody(BaseModel):
    confirm: bool = False


@router.post("/beats/{beat_id}/shots/plan")
def plan_shot(beat_id: str, c: Container = Depends(container)) -> dict[str, Any]:
    try:
        return c.shot_pipeline().plan_shot(beat_id).__dict__
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get("/shots/{shot_id}")
def get_shot(shot_id: str, c: Container = Depends(container)) -> dict[str, Any]:
    try:
        return c.shot_pipeline().get_shot(shot_id).__dict__
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
        if body.source_attempt_id:
            return c.shot_pipeline().render_from_attempt_draft(shot_id, body.source_attempt_id, seed=body.seed)
        return c.shot_pipeline().render(
            shot_id, use_pose=body.use_pose, pose_asset_uri=body.pose_asset_uri, seed=body.seed,
            camera_lock=CameraLockRequest(**body.camera_lock.model_dump()) if body.camera_lock else None
        )
    except CameraLockError as e:
        raise HTTPException(status_code=http_status_for_camera_code(e.code),
                            detail={"code": e.code, "message": str(e)}) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ComfyError as e:
        raise HTTPException(
            status_code=502,
            detail={"code": e.code.value, "message": str(e)},
        ) from e


@router.post("/shots/{shot_id}/prompt-draft")
def ensure_prompt_draft(shot_id: str, c: Container = Depends(container)) -> dict[str, Any]:
    try:
        return c.prompt_draft_service().ensure_for_shot(shot_id).to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get("/shots/{shot_id}/prompt-draft")
def get_prompt_draft(shot_id: str, c: Container = Depends(container)) -> dict[str, Any]:
    try:
        return c.prompt_draft_service().get_for_shot(shot_id).to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.put("/shots/{shot_id}/prompt-draft")
def put_prompt_draft(
    shot_id: str, body: PromptDraftEditBody, c: Container = Depends(container)
) -> dict[str, Any]:
    try:
        return c.prompt_draft_service().update_edits(
            shot_id, body.edited_positive, body.edited_negative
        ).to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/shots/{shot_id}/prompt-draft/reset-edits")
def reset_prompt_edits(shot_id: str, c: Container = Depends(container)) -> dict[str, Any]:
    try:
        return c.prompt_draft_service().reset_edits(shot_id).to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/shots/{shot_id}/prompt-draft/rebuild")
def rebuild_prompt_draft(
    shot_id: str,
    body: PromptDraftRebuildBody | None = None,
    c: Container = Depends(container),
) -> dict[str, Any]:
    try:
        payload = body or PromptDraftRebuildBody()
        return c.prompt_draft_service().rebuild(shot_id, confirm=payload.confirm).to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/shots/{shot_id}/prompt-template")
def get_prompt_template(shot_id: str, c: Container = Depends(container)) -> dict[str, Any]:
    try:
        return c.prompt_draft_service().template_for_shot(shot_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


def _attempt_detail(attempt: Any, c: Container) -> dict[str, Any]:
    return {
        "camera_stale": c.camera_lock_service().attempt_camera_staleness(attempt),
        "id": attempt.id,
        "render_plan_id": attempt.render_plan_id,
        "based_on_shot_revision": attempt.based_on_shot_revision,
        "status": attempt.status,
        "seed": attempt.seed,
        "payload": attempt.payload,
        "workflow_hash": attempt.workflow_hash,
        "output_asset_ids": attempt.output_asset_ids,
        "created_at": attempt.created_at.isoformat(),
        "final_positive_prompt": attempt.payload.get("final_positive_prompt"),
        "final_negative_prompt": attempt.payload.get("final_negative_prompt"),
        "prompt_hash": attempt.payload.get("prompt_hash"),
        "model_id": attempt.payload.get("model_id"),
        "modified": bool(attempt.payload.get("modified")),
        "source_kind": attempt.payload.get("source_kind"),
        "source_ref": attempt.payload.get("source_ref"),
        "template_id": attempt.payload.get("template_id"),
        "template_version": attempt.payload.get("template_version"),
    }


@router.get("/shots/{shot_id}/generation-attempts")
@router.get("/shots/{shot_id}/generations")
def list_generation_attempts(shot_id: str, c: Container = Depends(container)) -> dict[str, Any]:
    """List Attempts for a Shot (UI Spec R1: /generations)."""
    try:
        items = c.shot_pipeline().list_attempts_for_shot(shot_id)
        return {"items": items, "count": len(items)}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get("/generation-attempts/{attempt_id}")
@router.get("/generations/{attempt_id}")
def get_generation_attempt(attempt_id: str, c: Container = Depends(container)) -> dict[str, Any]:
    try:
        attempt = c.shot_pipeline().get_attempt(attempt_id)
        return _attempt_detail(attempt, c)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


class ReplayBody(BaseModel):
    seed_mode: Literal["new", "same"] = "new"
    copy_prompt_to_draft: bool = False


@router.post("/generations/{attempt_id}/replay")
def replay_generation(attempt_id: str, body: ReplayBody, c: Container = Depends(container)) -> dict[str, Any]:
    try:
        return c.shot_pipeline().replay(attempt_id, seed_mode=body.seed_mode,
                                        copy_prompt_to_draft=body.copy_prompt_to_draft)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ComfyError as exc:
        raise HTTPException(status_code=502, detail={"code": exc.code.value, "message": str(exc)}) from exc


@router.get("/generations/{attempt_id}/camera-qc")
def get_camera_qc(attempt_id: str, candidate_asset_id: str | None = None,
                  c: Container = Depends(container)) -> dict[str, Any]:
    try:
        attempt = c.shot_pipeline().get_attempt(attempt_id)
        if candidate_asset_id is not None and candidate_asset_id not in attempt.output_asset_ids:
            raise ValueError("candidate asset not found")
        reports = c.camera_qc_service().list_reports(attempt_id)
        return {"attempt_id": attempt_id, "items": [r.to_dict() for r in reports
                if candidate_asset_id is None or r.candidate_asset_id == candidate_asset_id]}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/generations/{attempt_id}/camera-qc")
def run_camera_qc(attempt_id: str, c: Container = Depends(container)) -> dict[str, Any]:
    try:
        reports = c.camera_qc_service().run_for_attempt(attempt_id)
        return {"attempt_id": attempt_id, "items": [r.to_dict() for r in reports]}
    except ValueError as exc:
        status = 400 if str(exc) == "attempt has no camera lock provenance" else 404
        raise HTTPException(status_code=status, detail=str(exc)) from exc
