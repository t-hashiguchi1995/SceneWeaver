from __future__ import annotations

from fastapi.testclient import TestClient

from apps.api.deps import container as container_dep
from apps.api.main import app
from creator_studio.application.e2e.visual_library_seed import seed_visual_library_catalog
from creator_studio.application.wardrobe.tryon import SeedMarketplaceItem


def test_visual_library_list_and_detail_api(container):
    seed_visual_library_catalog(
        container.uow(),
        container.store_asset(),
        SeedMarketplaceItem(container.uow()),
    )
    app.dependency_overrides[container_dep] = lambda: container
    try:
        with TestClient(app) as client:
            listed = client.get("/api/v1/visual-library")
            assert listed.status_code == 200, listed.text
            items = listed.json()
            assert len(items) >= 13
            for item in items:
                assert "prompt_fragment" not in item
                assert "payload_json" not in item
                assert item["ref"].startswith(item["source_type"] + ":")

            poses = client.get("/api/v1/visual-library", params={"kind": "pose"}).json()
            assert len(poses) == 3

            search = client.get("/api/v1/visual-library", params={"q": "振り向き"}).json()
            assert len(search) >= 1

            general = client.get(
                "/api/v1/visual-library", params={"content_rating": "general"}
            ).json()
            assert len(general) == len(items)

            anima = client.get("/api/v1/visual-library", params={"model": "anima"}).json()
            assert len(anima) == len(items)

            previewed = client.get(
                "/api/v1/visual-library", params={"has_preview": "true"}
            ).json()
            assert previewed
            assert all(i["has_preview"] for i in previewed)

            pose = next(i for i in poses if i.get("label_ja") == "振り向き")
            detail = client.get(
                f"/api/v1/visual-library/{pose['source_type']}/{pose['source_id']}"
            )
            assert detail.status_code == 200, detail.text
            body = detail.json()
            assert body["prompt_fragment"]
            assert "looking back" in body["prompt_fragment"]
            assert body["source"] == "e2e_visual_library"
            assert "payload_json" not in body

            missing = client.get("/api/v1/visual-library/prompt_preset/does-not-exist")
            assert missing.status_code == 404
    finally:
        app.dependency_overrides.clear()
