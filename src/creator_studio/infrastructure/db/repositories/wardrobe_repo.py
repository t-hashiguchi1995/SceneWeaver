from __future__ import annotations

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from creator_studio.domain.ids import AssetId, CharacterId
from creator_studio.domain.wardrobe import MarketplaceItem, OutfitProfile, TryOnSession
from creator_studio.infrastructure.db.models.wardrobe import (
    MarketplaceItemRow,
    OutfitProfileRow,
    TryOnSessionRow,
)


def _style_tags_blob(tags: list[str]) -> str:
    return " ".join(tags)


def _fts_match_query(raw: str) -> str:
    """Build a simple FTS5 MATCH expression from user text (token AND)."""
    tokens = [t for t in raw.lower().replace('"', " ").split() if t]
    if not tokens:
        return ""
    return " AND ".join(f'"{t}"' for t in tokens)


class SqlAlchemyMarketplaceRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, item: MarketplaceItem) -> MarketplaceItem:
        style_blob = _style_tags_blob(item.style_tags)
        self._session.add(
            MarketplaceItemRow(
                id=item.id,
                title=item.title,
                category=item.category,
                region=item.region,
                style_tags_json=item.style_tags,
                season_tags_json=item.season_tags,
                colors_json=item.colors,
                garment_description=item.garment_description,
                canonical_plate_asset_id=str(item.canonical_plate_asset_id)
                if item.canonical_plate_asset_id
                else None,
                source_json=item.source,
                verification_json=item.verification,
                search_text=" ".join(
                    [
                        item.title,
                        item.category,
                        item.region,
                        item.garment_description,
                        *item.style_tags,
                        *item.colors,
                    ]
                ).lower(),
                created_at=item.created_at,
            )
        )
        self._session.flush()
        self._session.execute(
            text(
                """
                INSERT INTO marketplace_items_fts(item_id, title, garment_description, style_tags)
                VALUES (:item_id, :title, :garment_description, :style_tags)
                """
            ),
            {
                "item_id": item.id,
                "title": item.title,
                "garment_description": item.garment_description,
                "style_tags": style_blob,
            },
        )
        return item

    def get(self, item_id: str) -> MarketplaceItem | None:
        row = self._session.get(MarketplaceItemRow, item_id)
        return self._from_row(row) if row else None

    def search(self, query: str = "", *, category: str | None = None) -> list[MarketplaceItem]:
        match = _fts_match_query(query)
        if match:
            return self._search_fts(match, category=category)
        return self._list_items(category=category)

    def _search_fts(self, match: str, *, category: str | None) -> list[MarketplaceItem]:
        fts_ids = list(
            self._session.execute(
                text(
                    """
                    SELECT item_id FROM marketplace_items_fts
                    WHERE marketplace_items_fts MATCH :q
                    ORDER BY rank
                    """
                ),
                {"q": match},
            ).scalars()
        )
        if not fts_ids:
            return []
        stmt = select(MarketplaceItemRow).where(MarketplaceItemRow.id.in_(fts_ids))
        if category:
            stmt = stmt.where(MarketplaceItemRow.category == category)
        by_id = {row.id: row for row in self._session.scalars(stmt)}
        return [self._from_row(by_id[item_id]) for item_id in fts_ids if item_id in by_id]

    def _list_items(self, *, category: str | None) -> list[MarketplaceItem]:
        stmt = select(MarketplaceItemRow)
        if category:
            stmt = stmt.where(MarketplaceItemRow.category == category)
        rows = self._session.scalars(stmt.order_by(MarketplaceItemRow.title.asc())).all()
        return [self._from_row(row) for row in rows]

    def _from_row(self, row: MarketplaceItemRow) -> MarketplaceItem:
        return MarketplaceItem(
            id=row.id,
            title=row.title,
            category=row.category,
            region=row.region,
            style_tags=list(row.style_tags_json or []),
            season_tags=list(row.season_tags_json or []),
            colors=list(row.colors_json or []),
            garment_description=row.garment_description,
            canonical_plate_asset_id=AssetId(row.canonical_plate_asset_id)
            if row.canonical_plate_asset_id
            else None,
            source=dict(row.source_json or {}),
            verification=dict(row.verification_json or {}),
            created_at=row.created_at,
        )


class SqlAlchemyOutfitProfileRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, profile: OutfitProfile) -> OutfitProfile:
        self._session.add(self._to_row(profile))
        return profile

    def get(self, profile_id: str) -> OutfitProfile | None:
        row = self._session.get(OutfitProfileRow, profile_id)
        return self._from_row(row) if row else None

    def list_for_character(self, character_id: str) -> list[OutfitProfile]:
        rows = self._session.scalars(
            select(OutfitProfileRow)
            .where(OutfitProfileRow.character_id == character_id)
            .order_by(OutfitProfileRow.updated_at.desc())
        ).all()
        return [self._from_row(row) for row in rows]

    def save(self, profile: OutfitProfile) -> OutfitProfile:
        row = self._session.get(OutfitProfileRow, profile.id)
        if row is None:
            return self.add(profile)
        fresh = self._to_row(profile)
        row.title = fresh.title
        row.semantic_json = fresh.semantic_json
        row.references_json = fresh.references_json
        row.updated_at = fresh.updated_at
        return profile

    def _to_row(self, profile: OutfitProfile) -> OutfitProfileRow:
        return OutfitProfileRow(
            id=profile.id,
            character_id=str(profile.character_id) if profile.character_id else None,
            title=profile.title,
            marketplace_item_id=profile.marketplace_item_id,
            semantic_json=profile.semantic,
            references_json=profile.references,
            created_at=profile.created_at,
            updated_at=profile.updated_at,
        )

    def _from_row(self, row: OutfitProfileRow) -> OutfitProfile:
        return OutfitProfile(
            id=row.id,
            character_id=CharacterId(row.character_id) if row.character_id else None,
            title=row.title,
            marketplace_item_id=row.marketplace_item_id,
            semantic=dict(row.semantic_json or {}),
            references=list(row.references_json or []),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )


class SqlAlchemyTryOnSessionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, session_obj: TryOnSession) -> TryOnSession:
        self._session.add(
            TryOnSessionRow(
                id=session_obj.id,
                character_id=str(session_obj.character_id),
                outfit_profile_id=session_obj.outfit_profile_id,
                source_asset_id=str(session_obj.source_asset_id),
                plate_asset_id=str(session_obj.plate_asset_id),
                status=session_obj.status,
                candidate_asset_ids_json=session_obj.candidate_asset_ids,
                adopted_asset_id=str(session_obj.adopted_asset_id)
                if session_obj.adopted_asset_id
                else None,
                created_at=session_obj.created_at,
            )
        )
        return session_obj

    def get(self, session_id: str) -> TryOnSession | None:
        row = self._session.get(TryOnSessionRow, session_id)
        if not row:
            return None
        return TryOnSession(
            id=row.id,
            character_id=CharacterId(row.character_id),
            outfit_profile_id=row.outfit_profile_id,
            source_asset_id=AssetId(row.source_asset_id),
            plate_asset_id=AssetId(row.plate_asset_id),
            status=row.status,
            candidate_asset_ids=list(row.candidate_asset_ids_json or []),
            adopted_asset_id=AssetId(row.adopted_asset_id) if row.adopted_asset_id else None,
            created_at=row.created_at,
        )

    def save(self, session_obj: TryOnSession) -> TryOnSession:
        row = self._session.get(TryOnSessionRow, session_obj.id)
        if row is None:
            return self.add(session_obj)
        row.status = session_obj.status
        row.candidate_asset_ids_json = session_obj.candidate_asset_ids
        row.adopted_asset_id = (
            str(session_obj.adopted_asset_id) if session_obj.adopted_asset_id else None
        )
        return session_obj