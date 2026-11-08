from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from apps.api.deps import container as container_dep
from apps.api.main import app
from creator_studio.application.assets.store_asset import StoreBytesCommand
from creator_studio.domain.asset import AssetKind


def test_editable_derived_lettering(container):
    output = BytesIO()
    Image.new("RGB", (800, 600), "blue").save(output, format="PNG")
    source = container.store_asset().execute(
        StoreBytesCommand(
            data=output.getvalue(),
            kind=AssetKind.GENERATED,
            mime="image/png",
            relative_dir="generated",
            filename="lettering-source.png",
        )
    )
    app.dependency_overrides[container_dep] = lambda: container
    try:
        with TestClient(app) as client:
            root = "/api/v1/lettering/layouts"
            response = client.post(
                root,
                json={
                    "image_asset_id": source.id,
                    "blocks": [
                        {
                            "text": "こんにちは",
                            "kind": "speech_bubble",
                            "anchor_xy_norm": [0.6, 0.6],
                        }
                    ],
                },
            )
            assert response.status_code == 200, response.text
            layout = response.json()
            url = root + "/" + layout["layout_id"]
            evaluation = client.post(
                url + "/evaluate",
                json={
                    "protected_regions": [
                        {"id": "face1", "role": "face", "bbox_xyxy_norm": [0.4, 0.4, 0.5, 0.5]}
                    ]
                },
            )
            assert evaluation.status_code == 200, evaluation.text
            quality = evaluation.json()
            assert (
                client.get("/api/v1/lettering/quality/" + quality["quality_evaluation_id"]).json()
                == quality
            )
            assert client.post(root + "/missing/evaluate", json={}).status_code == 404
            assert client.get("/api/v1/lettering/quality/missing").status_code == 404
            assert client.get(url).json() == layout
            layout["layers"][0].update(
                text="変更", shape="cloud", bbox_xyxy_norm=[0.1, 0.1, 0.4, 0.5]
            )
            edit = client.put(url, json={"layers": layout["layers"]})
            assert edit.status_code == 200, edit.text
            assert edit.json()["revision"] == 2
            assert client.get(url).json() == edit.json()
            result = client.post(url + "/render")
            assert result.status_code == 200, result.text
            asset = result.json()
            assert asset["kind"] == "derived" and asset["id"] != source.id
            assert asset["provenance"] == {
                "source_asset_id": source.id,
                "operation": "lettering",
                "layout_id": layout["layout_id"],
                "revision": 2,
            }
            assert asset["warnings"] == layout["warnings"]
            content = client.get(f"/api/v1/assets/{asset['id']}/content")
            with Image.open(BytesIO(content.content)) as image:
                assert image.size == (800, 600) and image.format == "PNG"
            assert client.get(f"/api/v1/assets/{source.id}/content").content == output.getvalue()
            assert client.get(root + "/missing").status_code == 404
            assert client.post(root + "/missing/render").status_code == 404
            assert client.put(root + "/missing", json={"layers": []}).status_code == 404
            assert (
                client.post(root, json={"image_asset_id": "missing", "blocks": []}).status_code
                == 404
            )
            assert (
                client.put(
                    url, json={"layers": [{"text": "bad", "bbox_xyxy_norm": [0, 0, 2, 1]}]}
                ).status_code
                == 422
            )
    finally:
        app.dependency_overrides.clear()
