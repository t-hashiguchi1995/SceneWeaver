from __future__ import annotations

import json
import os
from pathlib import Path

SERVICE = "sceneweaver"


class SecretStore:
    """OS keyring preferred; gitignored file fallback (never SQLite)."""

    def __init__(self, fallback_path: Path) -> None:
        self._fallback = fallback_path
        self._fallback.parent.mkdir(parents=True, exist_ok=True)
        self._backend = "keyring" if self._keyring_available() else "file"

    @property
    def backend(self) -> str:
        return self._backend

    @staticmethod
    def _keyring_available() -> bool:
        try:
            import keyring  # noqa: F401

            return True
        except Exception:
            return False

    def get(self, name: str) -> str | None:
        if self._backend == "keyring":
            try:
                import keyring

                value = keyring.get_password(SERVICE, name)
                if value:
                    return value
            except Exception:
                pass
        return self._file_load().get(name) or None

    def set(self, name: str, value: str) -> None:
        if self._backend == "keyring":
            try:
                import keyring

                keyring.set_password(SERVICE, name, value)
                return
            except Exception:
                self._backend = "file"
        data = self._file_load()
        data[name] = value
        self._file_write(data)

    def delete(self, name: str) -> None:
        if self._backend == "keyring":
            try:
                import keyring

                keyring.delete_password(SERVICE, name)
            except Exception:
                pass
        data = self._file_load()
        if name in data:
            del data[name]
            self._file_write(data)

    def _file_load(self) -> dict[str, str]:
        if not self._fallback.exists():
            return {}
        try:
            raw = json.loads(self._fallback.read_text(encoding="utf-8"))
            return raw if isinstance(raw, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def _file_write(self, data: dict[str, str]) -> None:
        self._fallback.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        try:
            os.chmod(self._fallback, 0o600)
        except OSError:
            pass
