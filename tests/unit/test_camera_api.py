from fastapi.testclient import TestClient

from apps.api.deps import container as container_dependency
from apps.api.main import create_app
from tests.unit.test_camera_lock import png, project, shot


def client_for(container):
    app = create_app()
    app.dependency_overrides[container_dependency] = lambda: container
    return TestClient(app)


def create(client, p, policy="not_required"):
    return client.post(
        f"/api/v1/projects/{p.id}/camera-rigs",
        json={"name": "Studio", "frame": {"width": 1536, "height": 864}, "face_policy": policy},
    )


def test_rig_api_revision(container):
    client = client_for(container)
    p = project(container)
    response = create(client, p)
    assert response.status_code == 200
    r = response.json()
    assert set(r) == {
        "id",
        "project_id",
        "name",
        "revision",
        "frame",
        "view",
        "anchor_asset_id",
        "background_mask_asset_id",
        "preservation_mode",
        "camera_device_visibility",
        "face_policy",
        "qc_profile_id",
        "status",
        "created_at",
        "updated_at",
    }
    assert r["frame"] == {"width": 1536, "height": 864, "aspect": "16:9"}
    assert client.get(f"/api/v1/projects/{p.id}/camera-rigs").json() == [r]
    assert client.get(f"/api/v1/camera-rigs/{r['id']}").json() == r
    response = client.put(
        f"/api/v1/camera-rigs/{r['id']}", json={"expected_revision": 99, "name": "Changed"}
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "CAMERA_RIG_STALE"


def test_anchor_and_binding_api(container):
    client = client_for(container)
    p = project(container)
    s = shot(container, p)
    r = create(client, p).json()
    asset = png(container)
    response = client.post(
        f"/api/v1/camera-rigs/{r['id']}/anchors", json={"image_asset_id": asset.id}
    )
    assert response.status_code == 200
    a = response.json()
    assert a["face_visibility"] == "unknown"
    assert a["anchor_asset_id"] == asset.id
    response = client.put(f"/api/v1/shots/{s.id}/camera-binding", json={"camera_rig_id": r["id"]})
    assert response.status_code == 200
    b = response.json()
    assert (b["rig_revision"], b["anchor_asset_sha256"]) == (r["revision"], a["sha256"])
    assert client.get(f"/api/v1/shots/{s.id}/camera-binding").json() == b
    strict = create(client, p, "full_visible").json()
    response = client.post(
        f"/api/v1/camera-rigs/{strict['id']}/anchors", json={"image_asset_id": asset.id}
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "ANCHOR_FACE_INVALID"
    assert "unverified" in response.json()["detail"]["message"]


def test_render_api_capability_and_plain_render(container):
    client = client_for(container)
    p = project(container)
    s = shot(container, p)
    r = create(client, p).json()
    asset = png(container)
    assert (
        client.post(
            f"/api/v1/camera-rigs/{r['id']}/anchors", json={"image_asset_id": asset.id}
        ).status_code
        == 200
    )
    assert (
        client.put(
            f"/api/v1/shots/{s.id}/camera-binding", json={"camera_rig_id": r["id"]}
        ).status_code
        == 200
    )
    response = client.post(f"/api/v1/shots/{s.id}/render", json={"camera_lock": {"enabled": True}})
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "CAMERA_LOCK_CAPABILITY_UNAVAILABLE"
    response = client.post(f"/api/v1/shots/{s.id}/render", json={})
    assert response.status_code == 200
    detail = client.get(f"/api/v1/generation-attempts/{response.json()['generation_attempt_id']}")
    assert detail.status_code == 200
    assert detail.json()["camera_stale"] is False
