from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from creator_studio.domain.ids import AssetId, CharacterId, new_id
from creator_studio.domain.timeutil import utc_now


@dataclass
class VisualIdentity:
    hair: str = ""
    eyes: str = ""
    body: str = ""
    identity_tags: list[str] = field(default_factory=list)
    identity_ref_asset_ids: list[str] = field(default_factory=list)
    tryon_base_asset_id: AssetId | None = None  # nullable; required only at Try-On start


@dataclass
class Persona:
    first_person: str = "私"
    second_person: str = "あなた"
    speech_rules: dict[str, Any] = field(default_factory=dict)
    forbidden_patterns: list[str] = field(default_factory=list)
    voice_examples: list[dict[str, Any]] = field(default_factory=list)
    max_chars: int = 40
    max_fragments: int = 2


@dataclass
class Character:
    id: CharacterId
    display_name: str
    visual_identity: VisualIdentity = field(default_factory=VisualIdentity)
    persona: Persona = field(default_factory=Persona)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    @classmethod
    def create(cls, display_name: str) -> Character:
        now = utc_now()
        return cls(
            id=CharacterId(new_id()),
            display_name=display_name.strip(),
            created_at=now,
            updated_at=now,
        )