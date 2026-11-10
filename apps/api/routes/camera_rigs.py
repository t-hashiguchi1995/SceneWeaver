from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict

from apps.api.deps import container
from creator_studio.domain.camera.errors import CameraLockError, http_status_for_camera_code
from creator_studio.infrastructure.container import Container

router = APIRouter(prefix="/api/v1", tags=["camera"])


class FrameBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    width: int
    height: int


class ViewBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: str = "reference_2d"
    azimuth_deg: float = 0
    elevation_deg: float = 12
    roll_deg: float = 0
    geometry_verified: bool = False


class CreateRigBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    frame: FrameBody
    view: ViewBody | None = None
    preservation_mode: str = "strict"
    camera_device_visibility: str = "forbidden"
    face_policy: str = "full_visible"
    qc_profile_id: str = "livestream_v1"
    background_mask_asset_id: str | None = None


class UpdateRigBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_revision: int
    name: str | None = None
    frame: FrameBody | None = None
    view: ViewBody | None = None
    preservation_mode: str | None = None
    camera_device_visibility: str | None = None
    face_policy: str | None = None
    qc_profile_id: str | None = None
    background_mask_asset_id: str | None = None
    status: str | None = None


class AnchorBody(BaseModel):
    image_asset_id: str
    bg_mask_asset_id: str | None = None


class BindingBody(BaseModel):
    camera_rig_id: str
    face_policy: str = "partial_allowed"
    subject_motion: str | None = None
    subject_distance_class: str | None = None
    edit_mask_asset_id: str | None = None
    pose_asset_id: str | None = None


def _call(operation, *, lookup=False):
    try:
        return operation()
    except CameraLockError as e:
        raise HTTPException(
            http_status_for_camera_code(e.code), detail={"code": e.code, "message": str(e)}
        ) from e
    except ValueError as e:
        status = 404 if lookup or str(e).endswith("not found") else 400
        raise HTTPException(status, detail=str(e)) from e


@router.post("/projects/{project_id}/camera-rigs")
def create_rig(project_id: str, body: CreateRigBody, c: Container = Depends(container)):
    values = body.model_dump(exclude={"frame", "view"})
    return _call(
        lambda: (
            c.camera_lock_service()
            .create_rig(
                project_id,
                frame_width=body.frame.width,
                frame_height=body.frame.height,
                view=body.view.model_dump(exclude_unset=True) if body.view else None,
                **values,
            )
            .to_dict()
        )
    )


@router.get("/projects/{project_id}/camera-rigs")
def list_rigs(project_id: str, c: Container = Depends(container)):
    return _call(
        lambda: [rig.to_dict() for rig in c.camera_lock_service().list_rigs(project_id)],
        lookup=True,
    )


@router.get("/camera-rigs/{rig_id}")
def get_rig(rig_id: str, c: Container = Depends(container)):
    return _call(lambda: c.camera_lock_service().get_rig(rig_id).to_dict(), lookup=True)


@router.put("/camera-rigs/{rig_id}")
def update_rig(rig_id: str, body: UpdateRigBody, c: Container = Depends(container)):
    return _call(
        lambda: (
            c.camera_lock_service()
            .update_rig(
                rig_id,
                expected_revision=body.expected_revision,
                patch=body.model_dump(exclude={"expected_revision"}, exclude_unset=True),
            )
            .to_dict()
        )
    )


@router.post("/camera-rigs/{rig_id}/anchors")
def register_anchor(rig_id: str, body: AnchorBody, c: Container = Depends(container)):
    def operation():
        svc = c.camera_lock_service()
        anchor = svc.register_anchor(rig_id, body.image_asset_id, body.bg_mask_asset_id)
        return {**anchor.to_dict(), "anchor_asset_id": svc.get_rig(rig_id).anchor_asset_id}

    return _call(operation)


@router.put("/shots/{shot_id}/camera-binding")
def bind_shot(shot_id: str, body: BindingBody, c: Container = Depends(container)):
    return _call(
        lambda: (
            c.camera_lock_service()
            .bind_shot(shot_id, body.camera_rig_id, **body.model_dump(exclude={"camera_rig_id"}))
            .to_dict()
        )
    )


@router.get("/shots/{shot_id}/camera-binding")
def get_binding(shot_id: str, c: Container = Depends(container)):
    binding = c.camera_lock_service().get_binding(shot_id)
    if binding is None:
        raise HTTPException(404, detail="camera binding not found")
    return binding.to_dict()
