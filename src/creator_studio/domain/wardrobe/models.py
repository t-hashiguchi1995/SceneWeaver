from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from creator_studio.domain.ids import AssetId, CharacterId, new_id
from creator_studio.domain.timeutil import utc_now


class VerificationStatus(StrEnum):
    UNTESTED = "untested"
    TESTED = "tested"
    VERIFIED = "verified"


@dataclass
class MarketplaceItem:
    id: str
    title: str
    category: str
    region: str
    style_tags: list[str] = field(default_factory=list)
    season_tags: list[str] = field(default_factory=list)
    colors: list[str] = field(default_factory=list)
    garment_description: str = ""
    canonical_plate_asset_id: AssetId | None = None
    source: dict[str, Any] = field(default_factory=dict)
    verification: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utc_now)

    @classmethod
    def create(cls, **kwargs: Any) -> MarketplaceItem:
        return cls(id=new_id(), **kwargs)


@dataclass
class OutfitProfile:
    id: str
    character_id: CharacterId | None
    title: str
    marketplace_item_id: str | None = None
    semantic: dict[str, Any] = field(default_factory=dict)
    references: list[dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    @classmethod
    def create(
        cls,
        title: str,
        *,
        character_id: CharacterId | None = None,
        marketplace_item_id: str | None = None,
        semantic: dict[str, Any] | None = None,
    ) -> OutfitProfile:
        now = utc_now()
        return cls(
            id=new_id(),
            character_id=character_id,
            title=title,
            marketplace_item_id=marketplace_item_id,
            semantic=semantic or {},
            created_at=now,
            updated_at=now,
        )

    def add_verified_reference(self, asset_id: AssetId, *, role: str = "tryon_verified") -> None:
        self.references.append(
            {
                "asset_id": str(asset_id),
                "role": role,
                "verification": VerificationStatus.VERIFIED.value,
            }
        )
        self.updated_at = utc_now()


@dataclass
class OutfitRecipe:
    """Schema reserved for Post-MVP Look Builder. Not executed in MVP."""

    id: str
    slots: dict[str, str] = field(default_factory=dict)
    compatibility: dict[str, Any] = field(default_factory=dict)


@dataclass
class OutfitState:
    outfit_profile_id: str


@dataclass
class TryOnSession:
    id: str
    character_id: CharacterId
    outfit_profile_id: str
    source_asset_id: AssetId
    plate_asset_id: AssetId
    status: str = "queued"
    candidate_asset_ids: list[str] = field(default_factory=list)
    adopted_asset_id: AssetId | None = None
    created_at: datetime = field(default_factory=utc_now)

    @classmethod
    def create(
        cls,
        *,
        character_id: CharacterId,
        outfit_profile_id: str,
        source_asset_id: AssetId,
        plate_asset_id: AssetId,
    ) -> TryOnSession:
        return cls(
            id=new_id(),
            character_id=character_id,
            outfit_profile_id=outfit_profile_id,
            source_asset_id=source_asset_id,
            plate_asset_id=plate_asset_id,
        )