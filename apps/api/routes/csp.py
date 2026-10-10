from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from apps.api.deps import container
from creator_studio.application.csp.handoff import HandoffError, PagePlan, PanelSlot
from creator_studio.infrastructure.container import Container

router = APIRouter(prefix="/api/v1", tags=["csp", "releases"])


class PanelIn(BaseModel):
    panel_no: int
    shot_id: str
    script_event_ids: list[str] = Field(default_factory=list)
    asset_id: str
    panel_slot_id: str | None = None


class PageIn(BaseModel):
    page_no: int
    panels: list[PanelIn]


class HandoffCreate(BaseModel):
    project_id: str
    pages: list[PageIn]
    script_rows: list[dict[str, str]] = Field(default_factory=list)
    revision: str | None = None


class ReleasePreviewCreate(BaseModel):
    title: str
    summary: str
    hashtags: list[str] = Field(default_factory=lambda: ["#SceneWeaver"])


@router.post("/csp/handoffs")
def create_handoff(body: HandoffCreate, c: Container = Depends(container)) -> dict[str, Any]:
    pages = [
        PagePlan(
            page_no=p.page_no,
            panels=[
                PanelSlot(
                    panel_no=panel.panel_no,
                    shot_id=panel.shot_id,
                    script_event_ids=panel.script_event_ids,
                    asset_id=panel.asset_id,
                    panel_slot_id=panel.panel_slot_id,
                )
                for panel in p.panels
            ],
        )
        for p in body.pages
    ]
    try:
        result = c.csp_handoff().build(
            body.project_id,
            pages,
            script_rows=body.script_rows,
            revision=body.revision,
        )
    except HandoffError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"revision": result.revision, "path": result.path, "manifest": result.manifest}


@router.post("/releases/preview")
def release_preview(body: ReleasePreviewCreate, c: Container = Depends(container)) -> dict[str, Any]:
    return c.release_preview().build_editions(
        title=body.title, summary=body.summary, hashtags=body.hashtags
    )
