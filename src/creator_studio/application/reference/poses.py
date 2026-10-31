"""Pose reference application service — Summary/Detail DTOs for API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from creator_studio.domain.reference import PoseDefinition
from creator_studio.infrastructure.reference.shisei_provider import ShiseiPoseProvider
from creator_studio.ports.reference_provider import ReferencePoseProvider


def asset_api_path(relative_path: str) -> str:
    # Clients never see data/ filesystem layout — opaque API path.
    return f"/api/v1/references/assets/{relative_path}"


@dataclass
class ReferencePoseService:
    provider: ReferencePoseProvider

    @classmethod
    def default(cls) -> ReferencePoseService:
        return cls(provider=ShiseiPoseProvider())

    def list_summaries(self) -> list[dict[str, Any]]:
        return [self.to_summary(p) for p in self.provider.list_poses()]

    def get_detail(self, pose_id: str) -> dict[str, Any] | None:
        pose = self.provider.get_pose(pose_id)
        if pose is None:
            return None
        return self.to_detail(pose)

    def resolve_asset_bytes(self, relative_path: str) -> tuple[bytes, str] | None:
        path = self.provider.resolve_asset_path(relative_path)
        if path is None:
            return None
        mime = "image/webp" if path.suffix.lower() == ".webp" else "application/octet-stream"
        if path.suffix.lower() == ".png":
            mime = "image/png"
        return path.read_bytes(), mime

    def to_summary(self, pose: PoseDefinition) -> dict[str, Any]:
        thumb_rel = pose.thumbnail_relative_path()
        return {
            "id": pose.id,
            "label": pose.label,
            "categories": list(pose.categories),
            "tags": list(pose.tags),
            "people_count": pose.people_count,
            "content_rating": pose.content_rating,
            "default_view": pose.default_view,
            "available_views": pose.available_views(),
            "thumbnail_url": asset_api_path(thumb_rel) if thumb_rel else None,
        }

    def to_detail(self, pose: PoseDefinition) -> dict[str, Any]:
        views: dict[str, Any] = {}
        for angle, view in pose.views.items():
            refs: dict[str, Any] = {}
            if view.line is not None:
                refs["line"] = {
                    "asset_id": view.line.asset_id,
                    "url": asset_api_path(view.line.relative_path),
                    "sha256": view.line.sha256,
                    "mime": view.line.mime,
                }
            views[angle] = {
                "id": view.id,
                "angle": view.angle,
                "prompt": view.prompt,
                "references": refs,
                "qc_status": view.qc_status,
            }
        return {
            **self.to_summary(pose),
            "views": views,
            "source": {
                "provider": pose.source.provider,
                "version": pose.source.version,
                "license": pose.source.license,
                "source_url": pose.source.source_url,
                "pack": pose.source.pack,
                "modality": pose.source.modality,
            },
        }

    def build_pose_provenance(
        self,
        *,
        pose_id: str,
        pose_view: str,
        flipped: bool = False,
        control_strength: float | None = None,
    ) -> dict[str, Any] | None:
        """Immutable snapshot for GenerationAttempt payload."""
        pose = self.provider.get_pose(pose_id)
        if pose is None:
            return None
        view = pose.views.get(pose_view)
        if view is None:
            return None
        line = view.line
        has_ref = line is not None
        return {
            "pose_id": pose.id,
            "pose_view": pose_view,
            "pose_method": "reference_image" if has_ref else "prompt",
            "pose_prompt": view.prompt,
            "pose_source": pose.source.provider,
            "pose_source_version": pose.source.version,
            "pose_asset_id": line.asset_id if line else None,
            "pose_asset_sha256": line.sha256 if line else None,
            "control_strength": control_strength if has_ref else None,
            "flipped": bool(flipped),
        }
