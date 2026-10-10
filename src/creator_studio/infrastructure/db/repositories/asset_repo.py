from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from creator_studio.domain.asset import Asset
from creator_studio.domain.ids import AssetId
from creator_studio.infrastructure.db.models import AssetRow
from creator_studio.infrastructure.db.repositories.mappers import asset_from_row, asset_to_row


class SqlAlchemyAssetRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, asset: Asset) -> Asset:
        self._session.add(asset_to_row(asset))
        return asset

    def get(self, asset_id: AssetId) -> Asset | None:
        row = self._session.get(AssetRow, str(asset_id))
        return asset_from_row(row) if row else None

    def find_by_sha256(self, sha256: str) -> Asset | None:
        row = self._session.scalars(select(AssetRow).where(AssetRow.sha256 == sha256)).first()
        return asset_from_row(row) if row else None

    def save(self, asset: Asset) -> Asset:
        row = self._session.get(AssetRow, str(asset.id))
        if row is None:
            return self.add(asset)
        row.metadata_json = asset.metadata
        row.provenance_json = asset.provenance
        row.kind = asset.kind.value
        return asset