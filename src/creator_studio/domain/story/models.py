from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from creator_studio.domain.ids import BeatId, CharacterId, ProjectId, SceneId, ScriptEventId, new_id
from creator_studio.domain.timeutil import utc_now


@dataclass
class EmotionSpec:
    name: str
    intensity: float = 0.5


@dataclass
class Scene:
    id: SceneId
    project_id: ProjectId
    seq: int
    title: str
    objective: str = ""
    initial_state: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    @classmethod
    def create(
        cls,
        project_id: ProjectId,
        seq: int,
        title: str,
        objective: str = "",
        initial_state: dict[str, Any] | None = None,
    ) -> Scene:
        now = utc_now()
        return cls(
            id=SceneId(new_id()),
            project_id=project_id,
            seq=seq,
            title=title,
            objective=objective,
            initial_state=initial_state or {},
            created_at=now,
            updated_at=now,
        )


@dataclass
class Beat:
    id: BeatId
    scene_id: SceneId
    seq: int
    intent: str
    subtext: str = ""
    emotion: EmotionSpec = field(default_factory=lambda: EmotionSpec(name="neutral"))
    action: str = ""
    speaker_id: CharacterId | None = None
    state_delta: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    @classmethod
    def create(
        cls,
        scene_id: SceneId,
        seq: int,
        intent: str,
        *,
        subtext: str = "",
        emotion: EmotionSpec | None = None,
        action: str = "",
        speaker_id: CharacterId | None = None,
        state_delta: dict[str, Any] | None = None,
    ) -> Beat:
        now = utc_now()
        return cls(
            id=BeatId(new_id()),
            scene_id=scene_id,
            seq=seq,
            intent=intent,
            subtext=subtext,
            emotion=emotion or EmotionSpec(name="neutral"),
            action=action,
            speaker_id=speaker_id,
            state_delta=state_delta or {},
            created_at=now,
            updated_at=now,
        )


class ScriptEventKind(StrEnum):
    SPEECH = "speech"
    INNER_VOICE = "inner_voice"
    NARRATION = "narration"
    CAPTION = "caption"
    OFFPANEL_VOICE = "offpanel_voice"
    SFX = "sfx"


class ScriptEventStatus(StrEnum):
    DRAFT = "draft"
    CANDIDATE = "candidate"
    SELECTED = "selected"
    LOCKED = "locked"
    SUPERSEDED = "superseded"


@dataclass
class ScriptEvent:
    id: ScriptEventId
    beat_id: BeatId
    kind: ScriptEventKind
    speaker_id: CharacterId | None
    text: str
    status: ScriptEventStatus = ScriptEventStatus.DRAFT
    locked: bool = False
    revision: int = 1
    tone: str = ""
    critic_scores: dict[str, Any] = field(default_factory=dict)
    director_plan: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    @classmethod
    def create_candidate(
        cls,
        beat_id: BeatId,
        *,
        kind: ScriptEventKind,
        speaker_id: CharacterId | None,
        text: str,
        tone: str = "",
        director_plan: dict[str, Any] | None = None,
        critic_scores: dict[str, Any] | None = None,
    ) -> ScriptEvent:
        now = utc_now()
        return cls(
            id=ScriptEventId(new_id()),
            beat_id=beat_id,
            kind=kind,
            speaker_id=speaker_id,
            text=text,
            status=ScriptEventStatus.CANDIDATE,
            tone=tone,
            director_plan=director_plan or {},
            critic_scores=critic_scores or {},
            created_at=now,
            updated_at=now,
        )

    def lock(self, text: str | None = None) -> None:
        if text is not None:
            self.text = text
        self.locked = True
        self.status = ScriptEventStatus.LOCKED
        # Bump revision so Shot invalidation can treat this as a script change.
        self.revision += 1
        self.updated_at = utc_now()

    def assert_unlocked_for_rewrite(self) -> None:
        if self.locked:
            raise PermissionError("locked ScriptEvent cannot be modified in place")


def resolve_effective_state(
    initial_state: dict[str, Any],
    deltas: list[dict[str, Any]],
) -> dict[str, Any]:
    state = dict(initial_state)
    for delta in deltas:
        state.update(delta)
    return state