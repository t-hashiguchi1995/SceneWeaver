from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from creator_studio.infrastructure.container import Container, reset_container
from creator_studio.infrastructure.db.migrate import upgrade_head
from creator_studio.infrastructure.db.session import reset_engine
from creator_studio.infrastructure.settings import Settings, clear_settings_cache


@pytest.fixture()
def tmp_runtime(tmp_path: Path) -> Path:
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    return runtime


@pytest.fixture()
def settings(tmp_runtime: Path, monkeypatch: pytest.MonkeyPatch) -> Settings:
    db = tmp_runtime / "test.db"
    monkeypatch.setenv("SCENEWEAVER_RUNTIME_DIR", str(tmp_runtime))
    monkeypatch.setenv("SCENEWEAVER_DATABASE_URL", f"sqlite:///{db}")
    monkeypatch.setenv("SCENEWEAVER_IMAGE_BACKEND", "fake")
    monkeypatch.setenv("SCENEWEAVER_WORKER_ID", "test-worker")
    clear_settings_cache()
    reset_engine()
    reset_container()
    return Settings()


@pytest.fixture()
def container(settings: Settings) -> Iterator[Container]:
    upgrade_head(settings.sqlalchemy_url())
    reset_engine()
    c = Container(settings)
    yield c
    reset_container()
    reset_engine()
    clear_settings_cache()
