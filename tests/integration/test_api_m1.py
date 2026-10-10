from __future__ import annotations

from fastapi.testclient import TestClient

from apps.api.main import create_app
from creator_studio.infrastructure.container import Container
from creator_studio.infrastructure.settings import Settings


def test_projects_jobs_capabilities_api(container: Container, settings: Settings) -> None:
    app = create_app()
    client = TestClient(app)

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["environment"] != "e2e"

    # Test control plane must never register outside e2e
    assert client.post("/api/test/reset").status_code == 404
    assert client.get("/api/test/state").status_code == 404

    created = client.post("/api/v1/projects", json={"title": "Demo"})
    assert created.status_code == 200
    project_id = created.json()["id"]

    listed = client.get("/api/v1/projects")
    assert any(p["id"] == project_id for p in listed.json())

    job = client.post("/api/v1/jobs", json={"kind": "stub", "payload": {"hello": True}})
    assert job.status_code == 200
    job_id = job.json()["id"]

    jobs = client.get("/api/v1/jobs")
    assert any(j["id"] == job_id for j in jobs.json())

    caps = client.get("/api/v1/capabilities")
    assert caps.status_code == 200
    body = caps.json()
    assert body["BaseRender"]["configured"] is True
    assert body["BaseRender"]["model_id"] == "anima_base"