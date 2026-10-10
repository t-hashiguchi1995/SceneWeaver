from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from creator_studio.infrastructure.settings.config import REPO_ROOT


def load_approved_model_ids(registry_path: Path | None = None) -> set[str]:
    path = registry_path or (REPO_ROOT / "config" / "model_registry.yaml")
    with path.open(encoding="utf-8") as f:
        data: dict[str, Any] = yaml.safe_load(f) or {}
    approved: dict[str, str] = data.get("approved_models") or {}
    return set(approved.values())


def resolve_template_id_for_capability(
    capability: str, registry_path: Path | None = None
) -> tuple[str, str]:
    """Return (model_id, template_id) for an approved capability."""
    path = registry_path or (REPO_ROOT / "config" / "model_registry.yaml")
    with path.open(encoding="utf-8") as f:
        data: dict[str, Any] = yaml.safe_load(f) or {}
    approved: dict[str, str] = data.get("approved_models") or {}
    models: dict[str, Any] = data.get("models") or {}
    if capability not in approved:
        raise ValueError(f"capability not approved: {capability}")
    model_id = approved[capability]
    model = models.get(model_id) or {}
    template_path = str(model.get("workflow_template") or "")
    # template file basename without suffix → id comes from YAML itself; map via loader
    return model_id, template_path
