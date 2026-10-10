from pathlib import Path

from creator_studio.adapters.secrets.store import SecretStore
from creator_studio.adapters.settings.file_store import FileUserSettingsStore
from creator_studio.application.settings.service import SettingsService
from creator_studio.infrastructure.settings import Settings


def test_user_settings_roundtrip_and_secret_not_in_json(tmp_path: Path) -> None:
    store = FileUserSettingsStore(tmp_path / "user_settings.json")
    secrets = SecretStore(tmp_path / "secrets.json")
    bootstrap = Settings(runtime_dir=str(tmp_path), environment="development")
    svc = SettingsService(store, secrets, bootstrap=bootstrap)

    out = svc.update(
        {
            "comfy_url": "http://127.0.0.1:8199",
            "image_backend": "comfy",
            "llm_provider": "openai_compatible",
            "llm_api_key": "sk-test-secret",
            "setup_completed": True,
        }
    )
    assert out["comfy_url"] == "http://127.0.0.1:8199"
    assert out["llm_api_key_set"] is True
    assert "llm_api_key" not in out
    assert "sk-test-secret" not in (tmp_path / "user_settings.json").read_text(encoding="utf-8")
    assert secrets.get("llm_api_key") == "sk-test-secret"


def test_harness_env_overrides_image_backend(tmp_path: Path) -> None:
    store = FileUserSettingsStore(tmp_path / "user_settings.json")
    secrets = SecretStore(tmp_path / "secrets.json")
    bootstrap = Settings(
        runtime_dir=str(tmp_path),
        environment="e2e",
        image_backend="fake",
    )
    svc = SettingsService(store, secrets, bootstrap=bootstrap)
    svc.update({"image_backend": "comfy"})
    assert svc.effective_image_backend() == "fake"
