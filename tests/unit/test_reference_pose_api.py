from fastapi.testclient import TestClient

from apps.api.main import create_app


def test_reference_pose_api_summary_and_detail() -> None:
    client = TestClient(create_app())
    listed = client.get("/api/v1/references/poses")
    assert listed.status_code == 200
    body = listed.json()
    assert len(body) >= 3
    item = body[0]
    assert "id" in item and "available_views" in item
    assert item["thumbnail_url"].startswith("/api/v1/references/assets/")
    assert "views" not in item  # Summary only

    detail = client.get(f"/api/v1/references/poses/{item['id']}")
    assert detail.status_code == 200
    d = detail.json()
    assert "views" in d and "source" in d
    assert d["source"]["provider"] == "shisei"
    view = d["views"][d["default_view"]]
    assert "prompt" in view
    assert view["references"]["line"]["url"].startswith("/api/v1/references/assets/")
    assert "sha256" in view["references"]["line"]

    asset = client.get(view["references"]["line"]["url"])
    assert asset.status_code == 200
    assert len(asset.content) > 100
    assert "image" in asset.headers.get("content-type", "")


def test_reference_pose_provenance_builder() -> None:
    from creator_studio.application.reference.poses import ReferencePoseService

    svc = ReferencePoseService.default()
    pose = svc.list_summaries()[0]
    detail = svc.get_detail(pose["id"])
    assert detail is not None
    view = detail["default_view"]
    snap = svc.build_pose_provenance(
        pose_id=pose["id"], pose_view=view, control_strength=1.0, flipped=False
    )
    assert snap is not None
    assert snap["pose_id"] == pose["id"]
    assert snap["pose_view"] == view
    assert snap["pose_source"] == "shisei"
    assert snap["pose_source_version"]
    assert snap["pose_asset_sha256"]
    assert snap["pose_method"] == "reference_image"
