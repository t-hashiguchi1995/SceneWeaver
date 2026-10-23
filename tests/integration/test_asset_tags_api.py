from __future__ import annotations

from fastapi.testclient import TestClient

from apps.api.deps import container as container_dep
from apps.api.main import app
from creator_studio.application.assets.store_asset import StoreBytesCommand
from creator_studio.domain.asset import AssetKind


def test_asset_tags_endpoint(container):
    dto = container.store_asset().execute(
        StoreBytesCommand(
            data=b"api-tags",
            kind=AssetKind.REFERENCE,
            mime="image/png",
            relative_dir="refs",
            filename="t.png",
        )
    )
    container.tag_asset().execute(dto.id)
    app.dependency_overrides[container_dep] = lambda: container
    try:
        with TestClient(app) as client:
            res = client.get(f"/api/v1/assets/{dto.id}/tags")
            assert res.status_code == 200, res.text
            tags = res.json()
            assert any(t["tag"] == "stub_auto" for t in tags)
            missing = client.get("/api/v1/assets/does-not-exist/tags")
            assert missing.status_code == 404
    finally:
        app.dependency_overrides.clear()
