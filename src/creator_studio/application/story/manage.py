from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from creator_studio.domain.ids import CharacterId, ProjectId, SceneId
from creator_studio.domain.story import Beat, EmotionSpec, Scene
from creator_studio.ports.unit_of_work import UnitOfWork


@dataclass
class SceneDTO:
    id: str
    project_id: str
    seq: int
    title: str
    objective: str
    initial_state: dict[str, Any]


@dataclass
class BeatDTO:
    id: str
    scene_id: str
    seq: int
    intent: str
    subtext: str
    emotion: dict[str, Any]
    action: str
    speaker_id: str | None
    state_delta: dict[str, Any]


def scene_dto(s: Scene) -> SceneDTO:
    return SceneDTO(
        id=str(s.id),
        project_id=str(s.project_id),
        seq=s.seq,
        title=s.title,
        objective=s.objective,
        initial_state=s.initial_state,
    )


def beat_dto(b: Beat) -> BeatDTO:
    return BeatDTO(
        id=str(b.id),
        scene_id=str(b.scene_id),
        seq=b.seq,
        intent=b.intent,
        subtext=b.subtext,
        emotion={"name": b.emotion.name, "intensity": b.emotion.intensity},
        action=b.action,
        speaker_id=str(b.speaker_id) if b.speaker_id else None,
        state_delta=b.state_delta,
    )


class CreateScene:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(
        self,
        project_id: str,
        title: str,
        *,
        objective: str = "",
        initial_state: dict[str, Any] | None = None,
    ) -> SceneDTO:
        with self._uow as uow:
            existing = uow.scenes.list_for_project(ProjectId(project_id))
            scene = Scene.create(
                ProjectId(project_id),
                seq=len(existing) + 1,
                title=title,
                objective=objective,
                initial_state=initial_state,
            )
            uow.scenes.add(scene)
            uow.commit()
            return scene_dto(scene)


class CreateBeat:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(
        self,
        scene_id: str,
        intent: str,
        *,
        subtext: str = "",
        emotion: dict[str, Any] | None = None,
        action: str = "",
        speaker_id: str | None = None,
        state_delta: dict[str, Any] | None = None,
    ) -> BeatDTO:
        with self._uow as uow:
            existing = uow.beats.list_for_scene(SceneId(scene_id))
            emo = emotion or {"name": "neutral", "intensity": 0.5}
            beat = Beat.create(
                SceneId(scene_id),
                seq=len(existing) + 1,
                intent=intent,
                subtext=subtext,
                emotion=EmotionSpec(name=str(emo["name"]), intensity=float(emo.get("intensity", 0.5))),
                action=action,
                speaker_id=CharacterId(speaker_id) if speaker_id else None,
                state_delta=state_delta,
            )
            uow.beats.add(beat)
            uow.commit()
            return beat_dto(beat)