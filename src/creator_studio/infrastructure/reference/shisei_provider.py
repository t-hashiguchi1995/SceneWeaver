"""Built-in Shisei-derived CC0 pose pack (SceneWeaver IDs only)."""

from __future__ import annotations

import json
from pathlib import Path

from creator_studio.domain.reference import PoseDefinition, PoseRefAsset, PoseSource, PoseView
from creator_studio.infrastructure.settings.config import REPO_ROOT

_DEFAULT_ROOT = REPO_ROOT / "data" / "reference" / "poses" / "shisei"


class ShiseiPoseProvider:
    def __init__(self, pack_root: Path | None = None) -> None:
        self._root = pack_root or _DEFAULT_ROOT
        self._by_id: dict[str, PoseDefinition] = {}
        self._load()

    def list_poses(self) -> list[PoseDefinition]:
        return list(self._by_id.values())

    def get_pose(self, pose_id: str) -> PoseDefinition | None:
        return self._by_id.get(pose_id)

    def resolve_asset_path(self, relative_path: str) -> Path | None:
        # Prevent path traversal
        rel = Path(relative_path)
        if rel.is_absolute() or ".." in rel.parts:
            return None
        path = (self._root / rel).resolve()
        try:
            path.relative_to(self._root.resolve())
        except ValueError:
            return None
        return path if path.is_file() else None

    def _load(self) -> None:
        catalog = self._root / "catalog.json"
        if not catalog.is_file():
            return
        data = json.loads(catalog.read_text(encoding="utf-8"))
        for entry in data.get("poses") or []:
            pose_dir = self._root / str(entry.get("path") or entry.get("id") or "")
            pose_json = pose_dir / "pose.json"
            if not pose_json.is_file():
                continue
            raw = json.loads(pose_json.read_text(encoding="utf-8"))
            pose = self._parse(raw)
            self._by_id[pose.id] = pose

    def _parse(self, raw: dict) -> PoseDefinition:
        src_raw = raw.get("source") or {}
        source = PoseSource(
            provider=str(src_raw.get("provider") or "shisei"),
            version=str(src_raw.get("version") or ""),
            license=str(src_raw.get("license") or "CC0-1.0"),
            source_url=str(src_raw.get("source_url") or ""),
            pack=str(src_raw.get("pack") or ""),
            modality=str(src_raw.get("modality") or "line"),
            original_asset_sha256={
                str(k): str(v) for k, v in (src_raw.get("original_asset_sha256") or {}).items()
            },
        )
        views: dict[str, PoseView] = {}
        for angle, vraw in (raw.get("views") or {}).items():
            refs = vraw.get("references") or {}
            line_raw = refs.get("line")
            line = None
            if isinstance(line_raw, dict) and line_raw.get("relative_path"):
                line = PoseRefAsset(
                    relative_path=str(line_raw["relative_path"]),
                    sha256=str(line_raw.get("sha256") or ""),
                    mime=str(line_raw.get("mime") or "image/webp"),
                    asset_id=line_raw.get("asset_id"),
                )
            views[str(angle)] = PoseView(
                id=str(vraw.get("id") or f"{raw['id']}-{angle}"),
                angle=angle,  # type: ignore[arg-type]
                prompt=str(vraw.get("prompt") or ""),
                line=line,
                qc_status=str(vraw.get("qc_status") or "unknown"),
            )
        return PoseDefinition(
            id=str(raw["id"]),
            label=str(raw.get("label") or raw["id"]),
            categories=tuple(str(x) for x in (raw.get("categories") or [])),
            tags=tuple(str(x) for x in (raw.get("tags") or [])),
            people_count=int(raw.get("people_count") or 1),
            content_rating=str(raw.get("content_rating") or "general"),
            default_view=str(raw.get("default_view") or "front"),  # type: ignore[arg-type]
            views=views,
            source=source,
        )
