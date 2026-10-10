from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from apps.api.deps import container
from creator_studio.infrastructure.container import Container

router = APIRouter(prefix="/api/v1", tags=["settings", "setup", "integrations"])


class SettingsPatch(BaseModel):
    setup_completed: bool | None = None
    workspace_label: str | None = None
    comfy_url: str | None = None
    image_backend: str | None = None
    llm_provider: str | None = None
    llm_base_url: str | None = None
    llm_model: str | None = None
    llm_api_key: str | None = Field(default=None, description="Write-only; never echoed back")
    eagle_enabled: bool | None = None
    eagle_base_url: str | None = None
    csp_export_dir: str | None = None
    recent_project_ids: list[str] | None = None


@router.get("/settings")
def get_settings_route(c: Container = Depends(container)) -> dict[str, Any]:
    return c.settings_service().get()


@router.put("/settings")
def put_settings(body: SettingsPatch, c: Container = Depends(container)) -> dict[str, Any]:
    return c.settings_service().update(body.model_dump(exclude_unset=True))


@router.get("/setup/status")
def setup_status(c: Container = Depends(container)) -> dict[str, Any]:
    settings = c.settings_service().get()
    diagnose = c.diagnose_comfy().execute(settings["comfy_url"]).to_dict()
    return {
        "setup_completed": bool(settings.get("setup_completed")),
        "workspace_label": settings.get("workspace_label"),
        "comfy": {
            "url": settings.get("comfy_url"),
            "reachable": diagnose["reachable"],
            "detail": diagnose["detail"],
            "ok": diagnose["ok"],
        },
        "llm": {
            "provider": settings.get("llm_provider"),
            "api_key_set": settings.get("llm_api_key_set"),
        },
        "eagle": {
            "enabled": settings.get("eagle_enabled"),
            "base_url": settings.get("eagle_base_url"),
        },
        "csp_export_dir": settings.get("csp_export_dir"),
        "secrets_backend": settings.get("secrets_backend"),
        "models": diagnose["models"],
        "nodes": diagnose["nodes"],
    }


@router.post("/setup/complete")
def setup_complete(c: Container = Depends(container)) -> dict[str, Any]:
    return c.settings_service().mark_setup_complete()


@router.post("/integrations/comfy/diagnose")
def diagnose_comfy(c: Container = Depends(container)) -> dict[str, Any]:
    url = c.settings_service().effective_comfy_url()
    return c.diagnose_comfy().execute(url).to_dict()
