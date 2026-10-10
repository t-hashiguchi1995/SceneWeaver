from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx
import yaml

from creator_studio.infrastructure.settings.config import REPO_ROOT

# Nodes required by SceneWeaver live workflows (minimal set).
_REQUIRED_NODES = [
    "CheckpointLoaderSimple",
    "UNETLoader",
    "CLIPLoader",
    "VAELoader",
    "KSampler",
    "LoadImage",
    "SaveImage",
    "TextEncodeQwenImageEditPlus",
    "AnimaLLLiteApply",
    "ModelPatchLoader",
    "EmptyLatentImage",
    "EmptySD3LatentImage",
    "VAEDecode",
]

_EXPECTED_MODELS: dict[str, list[str]] = {
    "anima_checkpoint": ["anima_baseV10.safetensors", "JANIMA_v10.safetensors"],
    "qwen_unet": ["qwen_image_edit_2509_fp8_e4m3fn.safetensors"],
    "qwen_clip": ["qwen_2.5_vl_7b_fp8_scaled.safetensors"],
    "qwen_vae": ["qwen_image_vae.safetensors"],
    "anima_lllite_pose": ["anima-lllite-pose-1.safetensors"],
}

_MODEL_FOLDERS = ("checkpoints", "unet", "diffusion_models", "vae", "clip", "loras", "model_patches")
_LOADER_KEYS = ("ckpt_name", "unet_name", "vae_name", "clip_name", "name", "lora_name")


@dataclass
class CheckItem:
    name: str
    ok: bool
    detail: str = ""


@dataclass
class ComfyDiagnoseResult:
    endpoint: str
    reachable: bool
    detail: str = ""
    models: list[CheckItem] = field(default_factory=list)
    nodes: list[CheckItem] = field(default_factory=list)
    capabilities: list[CheckItem] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        checks_ok = all(m.ok for m in self.models) and all(n.ok for n in self.nodes)
        return {
            "endpoint": self.endpoint,
            "reachable": self.reachable,
            "detail": self.detail,
            "ok": self.reachable and checks_ok,
            "models": [c.__dict__ for c in self.models],
            "nodes": [c.__dict__ for c in self.nodes],
            "capabilities": [c.__dict__ for c in self.capabilities],
        }


class DiagnoseComfy:
    def __init__(self, *, timeout: float = 8.0) -> None:
        self._timeout = timeout

    def execute(self, comfy_url: str) -> ComfyDiagnoseResult:
        base = comfy_url.rstrip("/")
        result = ComfyDiagnoseResult(endpoint=base, reachable=False)

        try:
            stats = httpx.get(f"{base}/system_stats", timeout=self._timeout)
        except Exception as exc:  # noqa: BLE001
            result.detail = f"{exc.__class__.__name__}: {exc}"
            return result
        if stats.status_code != 200:
            result.detail = f"HTTP {stats.status_code}"
            return result

        result.reachable = True
        result.detail = "comfy online"
        object_info = self._fetch_object_info(base, result)
        result.nodes = [
            CheckItem(
                name=node,
                ok=node in object_info,
                detail="present" if node in object_info else "missing custom node / type",
            )
            for node in _REQUIRED_NODES
        ]

        available = self._list_models(base, object_info)
        for label, candidates in _EXPECTED_MODELS.items():
            found = next((c for c in candidates if c in available), None)
            result.models.append(
                CheckItem(
                    name=label,
                    ok=found is not None,
                    detail=found or f"missing one of: {', '.join(candidates)}",
                )
            )
        result.capabilities = self._capability_checks()
        return result

    def _fetch_object_info(self, base: str, result: ComfyDiagnoseResult) -> dict[str, Any]:
        try:
            response = httpx.get(f"{base}/object_info", timeout=self._timeout)
            if response.status_code == 200:
                return response.json() or {}
        except Exception as exc:  # noqa: BLE001
            result.detail = f"online but object_info failed: {exc}"
        return {}

    def _capability_checks(self) -> list[CheckItem]:
        registry = yaml.safe_load(
            (REPO_ROOT / "config" / "model_registry.yaml").read_text(encoding="utf-8")
        ) or {}
        models = registry.get("models") or {}
        checks: list[CheckItem] = []
        for cap, model_id in (registry.get("approved_models") or {}).items():
            provider = (models.get(model_id) or {}).get("provider")
            if provider != "comfyui":
                continue
            checks.append(CheckItem(name=cap, ok=True, detail=f"model_id={model_id}"))
        return checks

    def _list_models(self, base: str, object_info: dict[str, Any]) -> set[str]:
        names: set[str] = set()
        for folder in _MODEL_FOLDERS:
            try:
                response = httpx.get(f"{base}/models/{folder}", timeout=self._timeout)
                if response.status_code == 200:
                    payload = response.json()
                    if isinstance(payload, list):
                        names.update(str(x) for x in payload)
            except Exception:
                continue
        for info in object_info.values():
            required = (info.get("input") or {}).get("required") or {}
            for key in _LOADER_KEYS:
                vals = required.get(key)
                if isinstance(vals, list) and vals and isinstance(vals[0], list):
                    names.update(str(x) for x in vals[0])
        return names
