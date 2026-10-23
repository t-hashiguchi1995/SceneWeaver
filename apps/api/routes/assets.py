from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

from apps.api.deps import container
from creator_studio.application.assets.store_asset import to_dto
from creator_studio.domain.ids import AssetId
from creator_studio.infrastructure.container import Container

router = APIRouter(prefix="/api/v1/assets", tags=["assets"])


class DecisionBody(BaseModel):
    decision: str = Field(description="adopted | rejected")


@router.get("/{asset_id}")
def get_asset(asset_id: str, c: Container = Depends(container)) -> dict[str, Any]:
    with c.uow() as uow:
        asset = uow.assets.get(AssetId(asset_id))
        if asset is None:
            raise HTTPException(status_code=404, detail="asset not found")
        return to_dto(asset).__dict__


@router.get("/{asset_id}/tags")
def get_asset_tags(asset_id: str, c: Container = Depends(container)) -> list[dict[str, Any]]:
    with c.uow() as uow:
        asset = uow.assets.get(AssetId(asset_id))
        if asset is None:
            raise HTTPException(status_code=404, detail="asset not found")
    return c.list_asset_tags().execute(asset_id)


@router.put("/{asset_id}/decision")
def set_decision(
    asset_id: str, body: DecisionBody, c: Container = Depends(container)
) -> dict[str, Any]:
    try:
        return c.set_asset_decision().execute(asset_id, body.decision)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{asset_id}/content")
def asset_content(asset_id: str, request: Request, c: Container = Depends(container)) -> Response:
    with c.uow() as uow:
        asset = uow.assets.get(AssetId(asset_id))
        if asset is None:
            raise HTTPException(status_code=404, detail="asset not found")
        try:
            path = c.asset_store.path_for_uri(asset.uri)
        except (ValueError, FileNotFoundError):
            raise HTTPException(status_code=404, detail="asset content not found")
        headers = {"ETag": f'"{asset.sha256}"', "Cache-Control": "private, max-age=3600",
                   "X-Content-Type-Options": "nosniff"}
        if request.headers.get("if-none-match") == headers["ETag"]:
            return Response(status_code=304, headers=headers)
        inline = asset.mime in {"image/png", "image/jpeg", "image/webp", "image/gif"}
        return FileResponse(path, media_type=asset.mime, headers=headers,
                            filename=path.name, content_disposition_type="inline" if inline else "attachment")
