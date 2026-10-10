from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from apps.api.deps import container
from creator_studio.infrastructure.container import Container

router = APIRouter(prefix="/api/v1/characters", tags=["characters"])


class CharacterCreate(BaseModel):
    display_name: str = Field(min_length=1, max_length=256)


class CharacterOut(BaseModel):
    id: str
    display_name: str
    visual_identity: dict[str, Any]
    persona: dict[str, Any]


@router.post("", response_model=CharacterOut)
def create_character(body: CharacterCreate, c: Container = Depends(container)) -> CharacterOut:
    dto = c.create_character().execute(body.display_name)
    return CharacterOut(**dto.__dict__)


@router.get("", response_model=list[CharacterOut])
def list_characters(c: Container = Depends(container)) -> list[CharacterOut]:
    return [CharacterOut(**x.__dict__) for x in c.list_characters().execute()]


@router.get("/{character_id}", response_model=CharacterOut)
def get_character(character_id: str, c: Container = Depends(container)) -> CharacterOut:
    dto = c.get_character().execute(character_id)
    if dto is None:
        raise HTTPException(status_code=404, detail="character not found")
    return CharacterOut(**dto.__dict__)


@router.put("/{character_id}/persona", response_model=CharacterOut)
def update_persona(
    character_id: str,
    body: dict[str, Any],
    c: Container = Depends(container),
) -> CharacterOut:
    try:
        dto = c.update_persona().execute(character_id, body)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return CharacterOut(**dto.__dict__)


@router.put("/{character_id}/visual-identity", response_model=CharacterOut)
def update_visual_identity(
    character_id: str,
    body: dict[str, Any],
    c: Container = Depends(container),
) -> CharacterOut:
    try:
        dto = c.update_visual_identity().execute(character_id, body)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return CharacterOut(**dto.__dict__)