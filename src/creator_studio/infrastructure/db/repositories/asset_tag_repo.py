from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from creator_studio.domain.asset_tag import AssetTag
from creator_studio.infrastructure.db.models.asset_tag import AssetTagRow


class SqlAlchemyAssetTagRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_for_asset(self, asset_id: str) -> list[AssetTag]:
        rows = self._session.scalars(
            select(AssetTagRow)
            .where(AssetTagRow.asset_id == asset_id)
            .order_by(AssetTagRow.score.desc(), AssetTagRow.tag)
        ).all()
        return [self._from_row(r) for r in rows]

    def list_for_assets(self, asset_ids: list[str]) -> list[AssetTag]:
        if not asset_ids:
            return []
        rows = self._session.scalars(
            select(AssetTagRow)
            .where(AssetTagRow.asset_id.in_(asset_ids))
            .order_by(AssetTagRow.score.desc(), AssetTagRow.tag)
        ).all()
        return [self._from_row(r) for r in rows]

    def upsert_many(self, tags: list[AssetTag]) -> list[AssetTag]:
        if not tags:
            return []
        # SQLite ON CONFLICT keeps re-runs idempotent for the unique identity.
        for tag in tags:
            stmt = (
                sqlite_insert(AssetTagRow)
                .values(
                    id=tag.id,
                    asset_id=tag.asset_id,
                    tag=tag.tag,
                    category=tag.category,
                    score=tag.score,
                    source_model=tag.source_model,
                    model_version=tag.model_version,
                    created_at=tag.created_at,
                )
                .on_conflict_do_update(
                    index_elements=["asset_id", "tag", "source_model", "model_version"],
                    set_={
                        "category": tag.category,
                        "score": tag.score,
                    },
                )
            )
            self._session.execute(stmt)
        return tags

    def replace_for_source(
        self,
        asset_id: str,
        source_model: str,
        model_version: str,
        tags: list[AssetTag],
    ) -> list[AssetTag]:
        """Atomically replace all tags for one (asset, source_model, model_version)."""
        self._session.execute(
            delete(AssetTagRow).where(
                AssetTagRow.asset_id == asset_id,
                AssetTagRow.source_model == source_model,
                AssetTagRow.model_version == model_version,
            )
        )
        for tag in tags:
            self._session.add(
                AssetTagRow(
                    id=tag.id,
                    asset_id=tag.asset_id,
                    tag=tag.tag,
                    category=tag.category,
                    score=tag.score,
                    source_model=tag.source_model,
                    model_version=tag.model_version,
                    created_at=tag.created_at,
                )
            )
        return self.list_for_asset(asset_id)

    def search_asset_ids(self, tag_query: str, *, limit: int = 200) -> list[str]:
        needle = tag_query.strip().lower()
        if not needle:
            return []
        rows = self._session.scalars(
            select(AssetTagRow.asset_id)
            .where(AssetTagRow.tag.ilike(f"%{needle}%"))
            .distinct()
            .limit(limit)
        ).all()
        return list(rows)

    @staticmethod
    def _from_row(row: AssetTagRow) -> AssetTag:
        return AssetTag(
            id=row.id,
            asset_id=row.asset_id,
            tag=row.tag,
            category=row.category,
            score=float(row.score),
            source_model=row.source_model,
            model_version=row.model_version,
            created_at=row.created_at,
        )
