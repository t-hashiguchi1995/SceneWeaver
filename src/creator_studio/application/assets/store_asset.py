from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from creator_studio.application.assets.tag_asset import schedule_asset_tagging
from creator_studio.domain.asset import Asset, AssetKind
from creator_studio.ports.asset_store import AssetStore
from creator_studio.ports.unit_of_work import UnitOfWork


@dataclass
class AssetDTO:
    id: str
    sha256: str
    uri: str
    kind: str
    mime: str
    byte_size: int
    metadata: dict[str, Any]
    provenance: dict[str, Any]


def to_dto(asset: Asset) -> AssetDTO:
    return AssetDTO(
        id=str(asset.id),
        sha256=asset.sha256,
        uri=asset.uri,
        kind=asset.kind.value,
        mime=asset.mime,
        byte_size=asset.byte_size,
        metadata=asset.metadata,
        provenance=asset.provenance,
    )


@dataclass
class StoreBytesCommand:
    data: bytes
    kind: AssetKind
    mime: str
    relative_dir: str
    filename: str
    metadata: dict[str, Any] | None = None
    provenance: dict[str, Any] | None = None


class StoreAssetBytes:
    def __init__(self, uow: UnitOfWork, store: AssetStore) -> None:
        self._uow = uow
        self._store = store

    def execute(self, cmd: StoreBytesCommand) -> AssetDTO:
        blob = self._store.put_bytes(
            cmd.data,
            relative_dir=cmd.relative_dir,
            filename=cmd.filename,
        )
        with self._uow as uow:
            existing = uow.assets.find_by_sha256(blob.sha256)
            if existing:
                return to_dto(existing)
            asset = Asset.create(
                sha256=blob.sha256,
                uri=blob.uri,
                kind=cmd.kind,
                mime=cmd.mime,
                byte_size=blob.byte_size,
                metadata=cmd.metadata,
                provenance=cmd.provenance,
            )
            uow.assets.add(asset)
            # Best-effort async tagging — never fails asset persistence.
            schedule_asset_tagging(uow, str(asset.id))
            uow.commit()
            return to_dto(asset)