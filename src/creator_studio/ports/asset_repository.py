from __future__ import annotations

from typing import Protocol

from creator_studio.domain.asset import Asset
from creator_studio.domain.ids import AssetId


class AssetRepository(Protocol):
    def add(self, asset: Asset) -> Asset: ...

    def get(self, asset_id: AssetId) -> Asset | None: ...

    def find_by_sha256(self, sha256: str) -> Asset | None: ...

    def save(self, asset: Asset) -> Asset: ...