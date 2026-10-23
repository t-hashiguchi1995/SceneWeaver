from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from creator_studio.domain.ids import new_id
from creator_studio.domain.timeutil import utc_now


@dataclass
class AssetTag:
    id: str
    asset_id: str
    tag: str
    category: str
    score: float
    source_model: str
    model_version: str
    created_at: datetime

    @classmethod
    def create(
        cls,
        *,
        asset_id: str,
        tag: str,
        category: str,
        score: float,
        source_model: str,
        model_version: str,
    ) -> AssetTag:
        return cls(
            id=new_id(),
            asset_id=asset_id,
            tag=tag,
            category=category,
            score=score,
            source_model=source_model,
            model_version=model_version,
            created_at=utc_now(),
        )
