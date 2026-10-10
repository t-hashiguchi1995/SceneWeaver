from __future__ import annotations

import json
from pathlib import Path

from creator_studio.application.settings.models import UserSettings


class FileUserSettingsStore:
    """Persist non-secret user preferences under runtime/user_settings.json."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> UserSettings:
        if not self._path.exists():
            return UserSettings()
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return UserSettings()
        return UserSettings.from_dict(raw if isinstance(raw, dict) else {})

    def save(self, settings: UserSettings) -> UserSettings:
        payload = settings.to_persist_dict()
        self._path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return settings
