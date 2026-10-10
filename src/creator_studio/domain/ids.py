from __future__ import annotations

import uuid
from typing import NewType

ProjectId = NewType("ProjectId", str)
JobId = NewType("JobId", str)
AssetId = NewType("AssetId", str)
CharacterId = NewType("CharacterId", str)
SceneId = NewType("SceneId", str)
BeatId = NewType("BeatId", str)
ScriptEventId = NewType("ScriptEventId", str)
ShotId = NewType("ShotId", str)


def new_id() -> str:
    # 26-char sortable-ish id (uuid4 hex truncated + time nbytes not needed for MVP)
    return uuid.uuid4().hex[:26]