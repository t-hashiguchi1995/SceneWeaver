"""Canonical Pose / Reference domain (Backend is source of truth)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

PoseAngle = Literal["front", "diag", "side", "above", "below"]


@dataclass(frozen=True)
class PoseRefAsset:
    """File-backed reference image; API exposes url, never filesystem paths to clients."""

    relative_path: str
    sha256: str
    mime: str = "image/webp"
    asset_id: str | None = None  # optional when ingested into AssetStore


@dataclass(frozen=True)
class PoseView:
    id: str
    angle: PoseAngle
    prompt: str
    line: PoseRefAsset | None = None
    depth: PoseRefAsset | None = None
    openpose: PoseRefAsset | None = None
    qc_status: str = "unknown"


@dataclass(frozen=True)
class PoseSource:
    provider: str
    version: str
    license: str
    source_url: str = ""
    pack: str = ""
    modality: str = "line"
    original_asset_sha256: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class PoseDefinition:
    """Canonical pose definition — Frontend consumes DTOs only."""

    id: str
    label: str
    categories: tuple[str, ...]
    tags: tuple[str, ...]
    people_count: int
    content_rating: str
    default_view: PoseAngle
    views: dict[str, PoseView]
    source: PoseSource

    def available_views(self) -> list[str]:
        return [a for a in ("front", "diag", "side", "above", "below") if a in self.views]

    def thumbnail_relative_path(self) -> str | None:
        view = self.views.get(self.default_view) or next(iter(self.views.values()), None)
        if view is None or view.line is None:
            return None
        return view.line.relative_path
