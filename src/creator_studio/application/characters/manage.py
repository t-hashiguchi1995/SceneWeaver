from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from creator_studio.domain.character import Character, Persona, VisualIdentity
from creator_studio.domain.ids import AssetId, CharacterId
from creator_studio.domain.timeutil import utc_now
from creator_studio.ports.unit_of_work import UnitOfWork


@dataclass
class CharacterDTO:
    id: str
    display_name: str
    visual_identity: dict[str, Any]
    persona: dict[str, Any]


def to_dto(c: Character) -> CharacterDTO:
    vi = c.visual_identity
    return CharacterDTO(
        id=str(c.id),
        display_name=c.display_name,
        visual_identity={
            "hair": vi.hair,
            "eyes": vi.eyes,
            "body": vi.body,
            "identity_tags": vi.identity_tags,
            "identity_ref_asset_ids": vi.identity_ref_asset_ids,
            "tryon_base_asset_id": str(vi.tryon_base_asset_id) if vi.tryon_base_asset_id else None,
        },
        persona={
            "first_person": c.persona.first_person,
            "second_person": c.persona.second_person,
            "speech_rules": c.persona.speech_rules,
            "forbidden_patterns": c.persona.forbidden_patterns,
            "voice_examples": c.persona.voice_examples,
            "max_chars": c.persona.max_chars,
            "max_fragments": c.persona.max_fragments,
        },
    )


class CreateCharacter:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, display_name: str) -> CharacterDTO:
        character = Character.create(display_name)
        with self._uow as uow:
            uow.characters.add(character)
            uow.commit()
        return to_dto(character)


class ListCharacters:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self) -> list[CharacterDTO]:
        with self._uow as uow:
            return [to_dto(c) for c in uow.characters.list()]


class GetCharacter:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, character_id: str) -> CharacterDTO | None:
        with self._uow as uow:
            c = uow.characters.get(CharacterId(character_id))
            return to_dto(c) if c else None


class UpdatePersona:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, character_id: str, persona: dict[str, Any]) -> CharacterDTO:
        with self._uow as uow:
            c = uow.characters.get(CharacterId(character_id))
            if c is None:
                raise ValueError("character not found")
            c.persona = Persona(
                first_person=persona.get("first_person", c.persona.first_person),
                second_person=persona.get("second_person", c.persona.second_person),
                speech_rules=persona.get("speech_rules", c.persona.speech_rules),
                forbidden_patterns=persona.get("forbidden_patterns", c.persona.forbidden_patterns),
                voice_examples=persona.get("voice_examples", c.persona.voice_examples),
                max_chars=int(persona.get("max_chars", c.persona.max_chars)),
                max_fragments=int(persona.get("max_fragments", c.persona.max_fragments)),
            )
            c.updated_at = utc_now()
            uow.characters.save(c)
            uow.commit()
            return to_dto(c)


class UpdateVisualIdentity:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, character_id: str, visual: dict[str, Any]) -> CharacterDTO:
        with self._uow as uow:
            c = uow.characters.get(CharacterId(character_id))
            if c is None:
                raise ValueError("character not found")
            tryon = visual.get("tryon_base_asset_id")
            c.visual_identity = VisualIdentity(
                hair=visual.get("hair", c.visual_identity.hair),
                eyes=visual.get("eyes", c.visual_identity.eyes),
                body=visual.get("body", c.visual_identity.body),
                identity_tags=visual.get("identity_tags", c.visual_identity.identity_tags),
                identity_ref_asset_ids=visual.get(
                    "identity_ref_asset_ids", c.visual_identity.identity_ref_asset_ids
                ),
                tryon_base_asset_id=AssetId(tryon) if tryon else None,
            )
            c.updated_at = utc_now()
            uow.characters.save(c)
            uow.commit()
            return to_dto(c)