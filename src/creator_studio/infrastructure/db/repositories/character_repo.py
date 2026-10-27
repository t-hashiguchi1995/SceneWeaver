from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from creator_studio.domain.character import Character, Persona, VisualIdentity
from creator_studio.domain.ids import AssetId, CharacterId
from creator_studio.infrastructure.db.models.character import CharacterRow


def _to_row(c: Character) -> CharacterRow:
    vi = c.visual_identity
    return CharacterRow(
        id=str(c.id),
        display_name=c.display_name,
        visual_identity_json={
            "hair": vi.hair,
            "eyes": vi.eyes,
            "body": vi.body,
            "identity_tags": vi.identity_tags,
            "identity_ref_asset_ids": vi.identity_ref_asset_ids,
            "tryon_base_asset_id": str(vi.tryon_base_asset_id) if vi.tryon_base_asset_id else None,
            "character_name": vi.character_name,
            "franchise": vi.franchise,
            "body_tags": vi.body_tags,
            "saved_anima_positive": vi.saved_anima_positive,
        },
        persona_json={
            "first_person": c.persona.first_person,
            "second_person": c.persona.second_person,
            "speech_rules": c.persona.speech_rules,
            "forbidden_patterns": c.persona.forbidden_patterns,
            "voice_examples": c.persona.voice_examples,
            "max_chars": c.persona.max_chars,
            "max_fragments": c.persona.max_fragments,
        },
        created_at=c.created_at,
        updated_at=c.updated_at,
    )


def _from_row(row: CharacterRow) -> Character:
    vi = row.visual_identity_json or {}
    pe = row.persona_json or {}
    tryon = vi.get("tryon_base_asset_id")
    return Character(
        id=CharacterId(row.id),
        display_name=row.display_name,
        visual_identity=VisualIdentity(
            hair=vi.get("hair", ""),
            eyes=vi.get("eyes", ""),
            body=vi.get("body", ""),
            identity_tags=list(vi.get("identity_tags") or []),
            identity_ref_asset_ids=list(vi.get("identity_ref_asset_ids") or []),
            tryon_base_asset_id=AssetId(tryon) if tryon else None,
            character_name=str(vi.get("character_name") or ""),
            franchise=str(vi.get("franchise") or ""),
            body_tags=list(vi.get("body_tags") or []),
            saved_anima_positive=str(vi.get("saved_anima_positive") or ""),
        ),
        persona=Persona(
            first_person=pe.get("first_person", "私"),
            second_person=pe.get("second_person", "あなた"),
            speech_rules=dict(pe.get("speech_rules") or {}),
            forbidden_patterns=list(pe.get("forbidden_patterns") or []),
            voice_examples=list(pe.get("voice_examples") or []),
            max_chars=int(pe.get("max_chars", 40)),
            max_fragments=int(pe.get("max_fragments", 2)),
        ),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class SqlAlchemyCharacterRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, character: Character) -> Character:
        self._session.add(_to_row(character))
        return character

    def get(self, character_id: CharacterId) -> Character | None:
        row = self._session.get(CharacterRow, str(character_id))
        return _from_row(row) if row else None

    def list(self) -> list[Character]:
        rows = self._session.scalars(
            select(CharacterRow).order_by(CharacterRow.created_at.desc())
        ).all()
        return [_from_row(r) for r in rows]

    def save(self, character: Character) -> Character:
        row = self._session.get(CharacterRow, str(character.id))
        if row is None:
            return self.add(character)
        fresh = _to_row(character)
        row.display_name = fresh.display_name
        row.visual_identity_json = fresh.visual_identity_json
        row.persona_json = fresh.persona_json
        row.updated_at = fresh.updated_at
        return character