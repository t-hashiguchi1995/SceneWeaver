from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from apps.api.deps import container as container_dep
from apps.api.main import app
from creator_studio.application.assets.store_asset import StoreBytesCommand
from creator_studio.domain.asset import AssetKind


def test_speech_bubble_creates_derived_asset(container):
    output = BytesIO()
    Image.new("RGB", (800, 600), "blue").save(output, format="PNG")
    original = output.getvalue()
    source = container.store_asset().execute(
        StoreBytesCommand(
            data=original,
            kind=AssetKind.GENERATED,
            mime="image/png",
            relative_dir="generated",
            filename="source.png",
        )
    )
    app.dependency_overrides[container_dep] = lambda: container
    try:
        with TestClient(app) as client:
            url = f"/api/v1/assets/{source.id}/speech-bubble"
            response = client.post(url, json={"text": "こんにちは！"})
            assert response.status_code == 200, response.text
            derived = response.json()
            assert derived["id"] != source.id
            assert derived["kind"] == "derived"
            assert derived["mime"] == "image/png"
            assert derived["provenance"] == {
                "source_asset_id": source.id,
                "operation": "speech_bubble",
                "text": "こんにちは！",
                "position": "top-right",
            }
            assert client.get(f"/api/v1/assets/{derived['id']}").json() == derived
            content = client.get(f"/api/v1/assets/{derived['id']}/content")
            assert content.status_code == 200
            with Image.open(BytesIO(content.content)) as image:
                assert image.format == "PNG"
                assert image.size == (800, 600)
            assert client.get(f"/api/v1/assets/{source.id}/content").content == original
            repeated = client.post(url, json={"text": "こんにちは！"})
            assert repeated.status_code == 200, repeated.text
            assert repeated.json()["id"] not in {source.id, derived["id"]}
            for text in ("", " \n "):
                assert client.post(url, json={"text": text}).status_code == 422
            assert client.post(url, json={"text": "台詞", "position": "center"}).status_code == 422
            assert (
                client.post(
                    "/api/v1/assets/missing/speech-bubble", json={"text": "台詞"}
                ).status_code
                == 404
            )
    finally:
        app.dependency_overrides.clear()
