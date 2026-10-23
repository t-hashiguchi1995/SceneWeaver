from __future__ import annotations

from typing import Protocol

from creator_studio.domain.asset_tag import AssetTag


class AssetTagRepository(Protocol):
    def list_for_asset(self, asset_id: str) -> list[AssetTag]: ...

    def list_for_assets(self, asset_ids: list[str]) -> list[AssetTag]: ...

    def upsert_many(self, tags: list[AssetTag]) -> list[AssetTag]: ...

    def replace_for_source(
        self,
        asset_id: str,
        source_model: str,
        model_version: str,
        tags: list[AssetTag],
    ) -> list[AssetTag]: ...

    def search_asset_ids(self, tag_query: str, *, limit: int = 200) -> list[str]: ...
