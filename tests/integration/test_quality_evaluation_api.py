from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from apps.api.deps import container as container_dep
from apps.api.main import app
from creator_studio.application.assets.store_asset import StoreBytesCommand
from creator_studio.application.image.quality_evaluation_store import load_evaluation
from creator_studio.domain.asset import AssetKind


def test_quality_evaluation_lifecycle(container):
    output = BytesIO()
    Image.new("RGB", (100, 100), "blue").save(output, format="PNG")
    source = container.store_asset().execute(
        StoreBytesCommand(
            data=output.getvalue(),
            kind=AssetKind.GENERATED,
            mime="image/png",
            relative_dir="generated",
            filename="source.png",
        )
    )
    app.dependency_overrides[container_dep] = lambda: container
    try:
        with TestClient(app) as client:
            create_url = f"/api/v1/assets/{source.id}/quality-evaluations"
            response = client.post(create_url)
            assert response.status_code == 200, response.text
            record = response.json()
            assert record["gate"] == "REVIEW"
            assert all(v is None for v in record["scores"].values())
            url = f"/api/v1/quality-evaluations/{record['quality_evaluation_id']}"
            assert client.get(url).json() == record
            reviewed = client.post(
                url + "/reviews",
                json={"reviewer_id": "human-1", "verdict": "PASS", "reasons": ["acceptable"]},
            )
            assert reviewed.status_code == 200, reviewed.text
            updated = reviewed.json()
            assert updated["human_verdict"] == "PASS"
            assert updated["reviewer_id"] == "human-1"
            assert updated["reviewed_at"]
            assert updated["gate"] == "REVIEW"
            assert client.get(url).json() == updated
            stored = load_evaluation(
                record["quality_evaluation_id"],
                directory=container.settings.runtime_path() / "quality_evaluations",
            )
            assert stored.to_dict() == updated
            repeated = client.post(create_url).json()
            assert repeated["findings"][0]["category"] == "duplicate"
            for body in (
                {},
                {"reviewer_id": "human"},
                {"verdict": "PASS"},
                {"reviewer_id": " ", "verdict": "PASS"},
            ):
                assert client.post(url + "/reviews", json=body).status_code == 422
            assert client.post("/api/v1/assets/missing/quality-evaluations").status_code == 404
            assert client.get("/api/v1/quality-evaluations/missing").status_code == 404
            assert (
                client.post(
                    "/api/v1/quality-evaluations/missing/reviews",
                    json={"reviewer_id": "human", "verdict": "PASS"},
                ).status_code
                == 404
            )
    finally:
        app.dependency_overrides.clear()
