from __future__ import annotations

import re
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml

from creator_studio.adapters.eagle.errors import EagleError, EagleErrorCode
from creator_studio.domain.asset.models import Asset, ReviewDecision
from creator_studio.infrastructure.filesystem.asset_store import FilesystemAssetStore
from creator_studio.infrastructure.settings.config import REPO_ROOT
from creator_studio.ports.eagle_gateway import EagleGateway
from creator_studio.ports.unit_of_work import UnitOfWork


def load_eagle_config() -> dict:
    config = (
        yaml.safe_load((REPO_ROOT / "config" / "integrations.yaml").read_text(encoding="utf-8"))
        or {}
    )
    return (config.get("integrations") or {}).get("eagle") or {}


def to_windows_path(wsl_path: str, *, wslpath_runner: Callable | None = None) -> str:
    if re.match(r"^[A-Za-z]:[\\/]", wsl_path) or wsl_path.startswith("\\\\"):
        return wsl_path
    match = re.match(r"^/mnt/([A-Za-z])/(.*)$", wsl_path)
    if match:
        return match[1].upper() + ":\\" + match[2].replace("/", "\\")
    try:
        result = (wslpath_runner or subprocess.run)(
            ["wslpath", "-w", wsl_path], capture_output=True, text=True, check=False
        )
        converted = result.stdout.strip()
        if result.returncode == 0 and (
            re.match(r"^[A-Za-z]:[\\/]", converted) or converted.startswith("\\\\")
        ):
            return converted
    except (OSError, subprocess.SubprocessError):
        pass
    raise EagleError(EagleErrorCode.EAGLE_PATH_UNCONVERTIBLE, wsl_path)


def _prompt(payload: Any, keys: tuple[str, ...]) -> str | None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key in keys and isinstance(value, str):
                return value
            found = _prompt(value, keys)
            if found is not None:
                return found
    elif isinstance(payload, list):
        for value in payload:
            found = _prompt(value, keys)
            if found is not None:
                return found
    return None


def build_annotation(asset: Asset, attempt: Any) -> str:
    payload = getattr(attempt, "payload", {})
    positive = _prompt(payload, ("positive", "edited_positive", "positive_prompt")) or "-"
    negative = _prompt(payload, ("negative", "edited_negative", "negative_prompt")) or "-"
    attempt_id = getattr(attempt, "id", None)
    seed = getattr(attempt, "seed", None)
    return (
        f"sw_asset:{asset.id} | sw_attempt:{attempt_id if attempt_id is not None else '-'}"
        f" | seed:{seed if seed is not None else '-'}\n{positive}\n{negative}"
    )


def build_tags(asset: Asset) -> list[str]:
    tags = ["sceneweaver", "status:adopted"]
    for prefix, keys in (
        ("char", ("character_name", "character", "char")),
        ("preset", ("preset_id", "preset")),
    ):
        value = next((asset.metadata[k] for k in keys if asset.metadata.get(k)), None)
        if value is not None:
            tags.append(f"{prefix}:{value}")
    return tags


@dataclass
class EagleSyncResult:
    status: Literal["synced", "already_synced", "dry_run"]
    eagle_item_id: str | None
    folder_id: str | None
    tags: list[str]
    annotation: str
    windows_path: str


class SyncAssetToEagle:
    def __init__(
        self,
        uow: UnitOfWork,
        gateway: EagleGateway,
        asset_store: FilesystemAssetStore,
        *,
        verify_attempts: int = 6,
        verify_interval_seconds: float = 1.0,
    ) -> None:
        self._uow = uow
        self._gateway = gateway
        self._asset_store = asset_store
        self._verify_attempts = verify_attempts
        self._verify_interval_seconds = verify_interval_seconds

    def execute(self, asset_id: str, *, dry_run: bool = False) -> EagleSyncResult:
        if not load_eagle_config().get("enabled", False):
            raise EagleError(EagleErrorCode.EAGLE_DISABLED, "Eagle integration is disabled")
        with self._uow as uow:
            asset = uow.assets.get(asset_id)
            if asset is None:
                raise EagleError(EagleErrorCode.ASSET_NOT_FOUND, asset_id)
            if asset.review_decision != ReviewDecision.ADOPTED:
                raise EagleError(EagleErrorCode.ASSET_NOT_ADOPTED, asset_id)
            attempt = None
            try:
                shot_id = asset.provenance.get("shot_id")
                if shot_id:
                    attempt = next(
                        (
                            a
                            for a in uow.generation_attempts.list_for_shot(shot_id)
                            if asset.id in a.output_asset_ids
                        ),
                        None,
                    )
            except Exception:  # noqa: BLE001 - provenance is best effort
                attempt = None
            tags = build_tags(asset)
            annotation = build_annotation(asset, attempt)
            try:
                path = (
                    self._asset_store.path_for_uri(asset.uri)
                    if asset.uri.startswith("asset://")
                    else Path(asset.uri)
                )
                if not path.is_file():
                    raise FileNotFoundError(asset.uri)
            except (OSError, ValueError) as exc:
                raise EagleError(EagleErrorCode.EAGLE_PATH_UNCONVERTIBLE, asset.uri) from exc
            windows_path = to_windows_path(str(path.resolve()))

        folders = self._gateway.list_folders()
        parent = next((f for f in folders if f.get("name") == "SceneWeaver"), None)
        child = next(
            (f for f in (parent or {}).get("children", []) if f.get("name") == "adopted"), None
        )
        folder_id = child["id"] if child else None
        offset = 0
        existing = None
        while True:
            items = self._gateway.list_items(limit=200, offset=offset)
            existing = next(
                (
                    item
                    for item in items
                    if f"sw_asset:{asset_id}" in (item.get("annotation") or "")
                ),
                None,
            )
            if existing or len(items) < 200:
                break
            offset += 200
        if dry_run:
            return EagleSyncResult("dry_run", None, folder_id, tags, annotation, windows_path)
        if existing:
            return EagleSyncResult(
                "already_synced", existing["id"], folder_id, tags, annotation, windows_path
            )
        if parent is None:
            parent = self._gateway.create_folder("SceneWeaver", None)
        if child is None:
            folder_id = self._gateway.create_folder("adopted", parent["id"])["id"]
        item = self._gateway.add_from_path(
            path=windows_path,
            name=path.stem,
            tags=tags,
            annotation=annotation,
            folder_id=folder_id,
        )
        item_id = item.get("id") if isinstance(item, dict) else item if isinstance(item, str) else None
        if not isinstance(item_id, str) or not item_id:
            raise EagleError(
                EagleErrorCode.EAGLE_API_ERROR, "addFromPath returned no valid item id"
            )
        for attempt in range(self._verify_attempts):
            if attempt:
                time.sleep(self._verify_interval_seconds)
            offset = 0
            while True:
                items = self._gateway.list_items(limit=200, offset=offset)
                registered = next(
                    (
                        item
                        for item in items
                        if f"sw_asset:{asset_id}" in (item.get("annotation") or "")
                    ),
                    None,
                )
                if registered:
                    return EagleSyncResult(
                        "synced", registered["id"], folder_id, tags, annotation, windows_path
                    )
                if len(items) < 200:
                    break
                offset += 200
        raise EagleError(
            EagleErrorCode.EAGLE_API_ERROR,
            f"Item returned by addFromPath ({item_id}) was not registered with our annotation "
            f"sw_asset:{asset_id}, possibly due to Eagle content-based deduplication",
        )
