from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

def find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists() and (parent / "config").is_dir():
            return parent
    return Path.cwd()


REPO_ROOT = find_repo_root()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="SCENEWEAVER_",
        extra="ignore",
    )

    environment: str = "development"  # development | e2e | live-test | production
    host: str = "127.0.0.1"
    port: int = 8000
    cors_origins: str = "http://127.0.0.1:5173,http://localhost:5173"
    runtime_dir: str = "runtime"
    database_url: str = "sqlite:///runtime/studio.db"
    worker_id: str = "worker-local-1"
    job_lease_seconds: int = 30
    llm_provider: str = "stub"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    comfy_url: str = "http://127.0.0.1:8188"
    image_backend: str = "fake"
    config_dir: str = "config"
    fake_image_delay_ms: int = 200
    comfy_poll_timeout_seconds: float = 300.0
    comfy_poll_interval_seconds: float = 2.0

    @property
    def is_e2e(self) -> bool:
        return self.environment.lower() == "e2e"

    @property
    def is_live_test(self) -> bool:
        return self.environment.lower() == "live-test"

    @property
    def allows_test_control(self) -> bool:
        """E2E + live-test harness may expose /api/test/* (never production)."""
        return self.environment.lower() in {"e2e", "live-test"}

    def runtime_path(self) -> Path:
        path = Path(self.runtime_dir)
        if not path.is_absolute():
            path = REPO_ROOT / path
        path.mkdir(parents=True, exist_ok=True)
        return path

    def repo_root(self) -> Path:
        return REPO_ROOT

    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def sqlalchemy_url(self) -> str:
        url = self.database_url
        if url.startswith("sqlite:///"):
            rest = url.removeprefix("sqlite:///")
            if rest != ":memory:" and not Path(rest).is_absolute():
                abs_path = self.runtime_path() / Path(rest).name
                if "runtime/" in rest or rest.startswith("runtime"):
                    abs_path = REPO_ROOT / rest
                abs_path.parent.mkdir(parents=True, exist_ok=True)
                return f"sqlite:///{abs_path}"
        return url

    def load_yaml(self, name: str) -> dict:
        path = self.repo_root() / self.config_dir / name
        with path.open(encoding="utf-8") as f:
            return yaml.safe_load(f) or {}


@lru_cache
def get_settings() -> Settings:
    return Settings()


def clear_settings_cache() -> None:
    get_settings.cache_clear()