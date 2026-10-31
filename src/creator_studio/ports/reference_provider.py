from __future__ import annotations

from pathlib import Path
from typing import Protocol

from creator_studio.domain.reference import PoseDefinition


class ReferencePoseProvider(Protocol):
    def list_poses(self) -> list[PoseDefinition]: ...

    def get_pose(self, pose_id: str) -> PoseDefinition | None: ...

    def resolve_asset_path(self, relative_path: str) -> Path | None:
        """Resolve pack-relative path to absolute file. Not exposed to clients."""
        ...
