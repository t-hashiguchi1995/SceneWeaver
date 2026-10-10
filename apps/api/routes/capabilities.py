from __future__ import annotations

from fastapi import APIRouter, Depends

from apps.api.deps import container
from apps.api.schemas import CapabilityOut
from creator_studio.infrastructure.container import Container

router = APIRouter(prefix="/api/v1/capabilities", tags=["capabilities"])


@router.get("", response_model=dict[str, CapabilityOut])
def list_capabilities(c: Container = Depends(container)) -> dict[str, CapabilityOut]:
    statuses = c.capabilities().list_capabilities()
    return {
        name: CapabilityOut(
            configured=s.configured,
            runtime_available=s.runtime_available,
            model_id=s.model_id,
            detail=s.detail,
        )
        for name, s in statuses.items()
    }