from __future__ import annotations

from dataclasses import asdict, replace
from typing import Any

from creator_studio.application.settings.models import UserSettings
from creator_studio.infrastructure.settings import Settings
from creator_studio.ports.user_settings import SecretVault, UserSettingsStore

LLM_API_KEY = "llm_api_key"
_MASK_PREFIX = "•"
_RECENT_LIMIT = 20


class SettingsService:
    def __init__(
        self,
        store: UserSettingsStore,
        secrets: SecretVault,
        *,
        bootstrap: Settings,
    ) -> None:
        self._store = store
        self._secrets = secrets
        self._bootstrap = bootstrap

    def get(self) -> dict[str, Any]:
        return self._public(self._merge_defaults(self._store.load()))

    def update(self, patch: dict[str, Any]) -> dict[str, Any]:
        data = asdict(self._merge_defaults(self._store.load()))
        for key, value in patch.items():
            if key == "llm_api_key":
                self._apply_llm_api_key(value)
                continue
            if key == "recent_project_ids":
                if isinstance(value, list):
                    data["recent_project_ids"] = [str(x) for x in value][:_RECENT_LIMIT]
                continue
            if key in data:
                data[key] = value
        return self._public(self._store.save(UserSettings(**data)))

    def mark_setup_complete(self) -> dict[str, Any]:
        return self.update({"setup_completed": True})

    def touch_recent_project(self, project_id: str) -> None:
        current = self._store.load()
        ids = [project_id, *[i for i in current.recent_project_ids if i != project_id]]
        self._store.save(replace(current, recent_project_ids=ids[:_RECENT_LIMIT]))

    def effective_comfy_url(self) -> str:
        user = self._store.load()
        return (user.comfy_url or self._bootstrap.comfy_url).rstrip("/")

    def effective_image_backend(self) -> str:
        # E2E / live-test process env wins — never let user settings override harness.
        if self._bootstrap.allows_test_control:
            return self._bootstrap.image_backend
        user = self._store.load()
        return user.image_backend or self._bootstrap.image_backend

    def llm_api_key(self) -> str:
        return self._secrets.get(LLM_API_KEY) or self._bootstrap.llm_api_key or ""

    def _apply_llm_api_key(self, value: Any) -> None:
        if value is None or value == "":
            self._secrets.delete(LLM_API_KEY)
            return
        text = str(value)
        if text.startswith(_MASK_PREFIX):
            return
        self._secrets.set(LLM_API_KEY, text)

    def _public(self, user: UserSettings) -> dict[str, Any]:
        return user.to_public_dict(
            has_llm_api_key=bool(self.llm_api_key()),
            secrets_backend=self._secrets.backend,
        )

    def _merge_defaults(self, user: UserSettings) -> UserSettings:
        b = self._bootstrap
        return UserSettings(
            setup_completed=user.setup_completed,
            workspace_label=user.workspace_label or str(b.runtime_path()),
            comfy_url=user.comfy_url or b.comfy_url,
            image_backend=user.image_backend or b.image_backend,
            llm_provider=user.llm_provider or b.llm_provider,
            llm_base_url=user.llm_base_url or b.llm_base_url,
            llm_model=user.llm_model or b.llm_model,
            eagle_enabled=user.eagle_enabled,
            eagle_base_url=user.eagle_base_url,
            csp_export_dir=user.csp_export_dir,
            recent_project_ids=list(user.recent_project_ids),
        )
