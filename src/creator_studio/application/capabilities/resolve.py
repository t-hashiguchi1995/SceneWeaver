from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from creator_studio.ports.runtime_probe import ProviderHealth, RuntimeCapabilityProbe


@dataclass
class CapabilityStatus:
    configured: bool
    runtime_available: bool
    model_id: str | None
    detail: str = ""


class CapabilityService:
    """Assembles approved registry + runtime probe results (no HTTP / URLs)."""

    def __init__(
        self,
        registry_path: Path,
        *,
        comfy_probe: RuntimeCapabilityProbe,
        other_probes: dict[str, RuntimeCapabilityProbe] | None = None,
    ) -> None:
        self._registry_path = registry_path
        self._comfy_probe = comfy_probe
        self._other_probes = other_probes or {}

    def _load(self) -> dict[str, Any]:
        with self._registry_path.open(encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def _health_for(
        self,
        provider: str | None,
        *,
        comfy_health: ProviderHealth,
    ) -> ProviderHealth:
        if provider == "comfyui":
            return comfy_health
        if provider == "google":
            probe = self._other_probes.get("google")
            if probe is None:
                return ProviderHealth(available=False, detail="google provider not probed in MVP")
            return probe.probe()
        return ProviderHealth(available=False, detail=f"unknown provider: {provider}")

    def list_capabilities(self) -> dict[str, CapabilityStatus]:
        data = self._load()
        approved: dict[str, str] = data.get("approved_models", {})
        models: dict[str, Any] = data.get("models", {})
        comfy_health = self._comfy_probe.probe()

        result: dict[str, CapabilityStatus] = {}
        for capability, model_id in approved.items():
            model = models.get(model_id)
            if model is None:
                result[capability] = CapabilityStatus(
                    configured=False,
                    runtime_available=False,
                    model_id=model_id,
                    detail="model missing from registry",
                )
                continue

            health = self._health_for(model.get("provider"), comfy_health=comfy_health)
            result[capability] = CapabilityStatus(
                configured=True,
                runtime_available=health.available,
                model_id=model_id,
                detail=health.detail,
            )
        return result

    def resolve_model(self, capability: str) -> str:
        approved: dict[str, str] = self._load().get("approved_models", {})
        if capability not in approved:
            raise ValueError(f"capability not approved: {capability}")
        return approved[capability]
