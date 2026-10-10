from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from creator_studio.domain.ids import BeatId, ShotId, new_id
from creator_studio.domain.timeutil import utc_now


@dataclass
class ShotSpec:
    id: ShotId
    beat_id: BeatId
    revision: int
    render_spec: dict[str, Any]
    stale_reason: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    @classmethod
    def create(cls, beat_id: BeatId, render_spec: dict[str, Any], revision: int = 1) -> ShotSpec:
        now = utc_now()
        return cls(
            id=ShotId(new_id()),
            beat_id=beat_id,
            revision=revision,
            render_spec=render_spec,
            created_at=now,
            updated_at=now,
        )

    @property
    def is_stale(self) -> bool:
        return self.stale_reason is not None

    def mark_stale(self, reason: str) -> None:
        self.stale_reason = reason
        self.updated_at = utc_now()


@dataclass
class RenderPlan:
    id: str
    shot_id: ShotId
    shot_revision: int
    capability: str
    provider: str
    template_id: str
    refs: dict[str, str] = field(default_factory=dict)
    stale_reason: str | None = None
    created_at: datetime = field(default_factory=utc_now)

    @classmethod
    def create(
        cls,
        shot_id: ShotId,
        shot_revision: int,
        *,
        capability: str,
        provider: str,
        template_id: str,
        refs: dict[str, str] | None = None,
    ) -> RenderPlan:
        return cls(
            id=new_id(),
            shot_id=shot_id,
            shot_revision=shot_revision,
            capability=capability,
            provider=provider,
            template_id=template_id,
            refs=refs or {},
        )


@dataclass
class GenerationAttempt:
    """Immutable generation record. current/stale is derived from shot revision."""

    id: str
    render_plan_id: str
    based_on_shot_revision: int
    status: str
    seed: int
    payload: dict[str, Any] = field(default_factory=dict)
    workflow_hash: str = ""
    output_asset_ids: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=utc_now)

    @classmethod
    def create(
        cls,
        render_plan_id: str,
        based_on_shot_revision: int,
        *,
        seed: int,
        payload: dict[str, Any],
        workflow_hash: str,
        status: str = "succeeded",
        output_asset_ids: list[str] | None = None,
    ) -> GenerationAttempt:
        return cls(
            id=new_id(),
            render_plan_id=render_plan_id,
            based_on_shot_revision=based_on_shot_revision,
            status=status,
            seed=seed,
            payload=payload,
            workflow_hash=workflow_hash,
            output_asset_ids=output_asset_ids or [],
        )

    def is_current_for(self, shot_revision: int) -> bool:
        return self.based_on_shot_revision == shot_revision