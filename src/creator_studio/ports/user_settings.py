from __future__ import annotations

from typing import Protocol

from creator_studio.application.settings.models import UserSettings


class UserSettingsStore(Protocol):
    def load(self) -> UserSettings: ...

    def save(self, settings: UserSettings) -> UserSettings: ...


class SecretVault(Protocol):
    @property
    def backend(self) -> str: ...

    def get(self, name: str) -> str | None: ...

    def set(self, name: str, value: str) -> None: ...

    def delete(self, name: str) -> None: ...
