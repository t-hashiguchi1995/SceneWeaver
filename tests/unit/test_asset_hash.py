from __future__ import annotations

from creator_studio.application.assets.store_asset import StoreBytesCommand
from creator_studio.domain.asset import AssetKind
from creator_studio.infrastructure.container import Container


def test_asset_store_dedupes_by_sha256(container: Container) -> None:
    store = container.store_asset()
    data = b"hello-sceneweaver"
    first = store.execute(
        StoreBytesCommand(
            data=data,
            kind=AssetKind.IMPORTED,
            mime="application/octet-stream",
            relative_dir="imported",
            filename="a.bin",
        )
    )
    second = store.execute(
        StoreBytesCommand(
            data=data,
            kind=AssetKind.IMPORTED,
            mime="application/octet-stream",
            relative_dir="imported",
            filename="b.bin",
        )
    )
    assert first.sha256 == second.sha256
    assert first.id == second.id
    assert first.uri.startswith("asset://")