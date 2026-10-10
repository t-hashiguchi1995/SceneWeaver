from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
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


@router.put("/{asset_id}/decision")
def set_decision(
    asset_id: str, body: DecisionBody, c: Container = Depends(container)
) -> dict[str, Any]:
    try:
        return c.set_asset_decision().execute(asset_id, body.decision)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
