from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from typing import Any


@dataclass
class UserSettings:
    """Non-secret preferences (persisted as JSON under runtime/)."""

    setup_completed: bool = False
    workspace_label: str = ""
    comfy_url: str = "http://127.0.0.1:8188"
    image_backend: str = "fake"  # fake | comfy | comfy_dry
    llm_provider: str = "stub"  # stub | openai_compatible
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    eagle_enabled: bool = False
    eagle_base_url: str = ""
    csp_export_dir: str = ""
    recent_project_ids: list[str] = field(default_factory=list)

    def to_public_dict(self, *, has_llm_api_key: bool, secrets_backend: str) -> dict[str, Any]:
        data = asdict(self)
        data["llm_api_key_set"] = has_llm_api_key
        data["secrets_backend"] = secrets_backend
        return data

    def to_persist_dict(self) -> dict[str, Any]:
        """JSON-safe payload with no secret fields."""
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, Any] | None) -> UserSettings:
        if not raw:
            return cls()
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in raw.items() if k in known})
