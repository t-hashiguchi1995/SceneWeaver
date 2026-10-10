from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from apps.api.deps import container
from creator_studio.infrastructure.container import Container

router = APIRouter(prefix="/api/v1", tags=["story"])


class SceneCreate(BaseModel):
    title: str = Field(min_length=1)
    objective: str = ""
    initial_state: dict[str, Any] = Field(default_factory=dict)


class BeatCreate(BaseModel):
    intent: str = Field(min_length=1)
    subtext: str = ""
    emotion: dict[str, Any] = Field(default_factory=lambda: {"name": "neutral", "intensity": 0.5})
    action: str = ""
    speaker_id: str | None = None
    state_delta: dict[str, Any] = Field(default_factory=dict)


class DialogueGenerate(BaseModel):
    character_id: str
    candidate_count: int = 3


class ScriptLock(BaseModel):
    text: str | None = None


@router.post("/projects/{project_id}/scenes")
def create_scene(
    project_id: str,
    body: SceneCreate,
    c: Container = Depends(container),
) -> dict[str, Any]:
    dto = c.create_scene().execute(
        project_id,
        body.title,
        objective=body.objective,
        initial_state=body.initial_state,
    )
    return dto.__dict__


@router.post("/scenes/{scene_id}/beats")
def create_beat(
    scene_id: str,
    body: BeatCreate,
    c: Container = Depends(container),
) -> dict[str, Any]:
    dto = c.create_beat().execute(
        scene_id,
        body.intent,
        subtext=body.subtext,
        emotion=body.emotion,
        action=body.action,
        speaker_id=body.speaker_id,
        state_delta=body.state_delta,
    )
    return dto.__dict__


@router.post("/beats/{beat_id}/script-events/candidates")
def generate_candidates(
    beat_id: str,
    body: DialogueGenerate,
    c: Container = Depends(container),
) -> dict[str, Any]:
    try:
        result = c.dialogue_pipeline().generate_candidates(
            beat_id=beat_id,
            character_id=body.character_id,
            candidate_count=body.candidate_count,
        )
    except PermissionError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return {
        "director_plan": result.director_plan,
        "voice_examples": result.voice_examples,
        "candidates": [c.__dict__ for c in result.candidates],
    }


@router.put("/script-events/{event_id}/lock")
def lock_script_event(
    event_id: str,
    body: ScriptLock,
    c: Container = Depends(container),
) -> dict[str, Any]:
    try:
        event = c.dialogue_pipeline().lock_script_event(event_id, body.text)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return {
        "id": str(event.id),
        "text": event.text,
        "locked": event.locked,
        "status": event.status.value,
        "revision": event.revision,
    }