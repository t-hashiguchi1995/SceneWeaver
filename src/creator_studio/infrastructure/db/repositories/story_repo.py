from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from creator_studio.domain.ids import BeatId, CharacterId, ProjectId, SceneId, ScriptEventId
from creator_studio.domain.story import (
    Beat,
    EmotionSpec,
    Scene,
    ScriptEvent,
    ScriptEventKind,
    ScriptEventStatus,
)
from creator_studio.infrastructure.db.models.story import BeatRow, SceneRow, ScriptEventRow


class SqlAlchemySceneRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, scene: Scene) -> Scene:
        self._session.add(
            SceneRow(
                id=str(scene.id),
                project_id=str(scene.project_id),
                seq=scene.seq,
                title=scene.title,
                objective=scene.objective,
                initial_state_json=scene.initial_state,
                created_at=scene.created_at,
                updated_at=scene.updated_at,
            )
        )
        return scene

    def get(self, scene_id: SceneId) -> Scene | None:
        row = self._session.get(SceneRow, str(scene_id))
        if not row:
            return None
        return Scene(
            id=SceneId(row.id),
            project_id=ProjectId(row.project_id),
            seq=row.seq,
            title=row.title,
            objective=row.objective,
            initial_state=dict(row.initial_state_json or {}),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def list_for_project(self, project_id: ProjectId) -> list[Scene]:
        rows = self._session.scalars(
            select(SceneRow)
            .where(SceneRow.project_id == str(project_id))
            .order_by(SceneRow.seq.asc())
        ).all()
        return [self.get(SceneId(r.id)) for r in rows]  # type: ignore[misc]

    def save(self, scene: Scene) -> Scene:
        row = self._session.get(SceneRow, str(scene.id))
        if row is None:
            return self.add(scene)
        row.title = scene.title
        row.objective = scene.objective
        row.initial_state_json = scene.initial_state
        row.updated_at = scene.updated_at
        return scene


class SqlAlchemyBeatRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, beat: Beat) -> Beat:
        self._session.add(
            BeatRow(
                id=str(beat.id),
                scene_id=str(beat.scene_id),
                seq=beat.seq,
                intent=beat.intent,
                subtext=beat.subtext,
                emotion_json={"name": beat.emotion.name, "intensity": beat.emotion.intensity},
                action=beat.action,
                speaker_id=str(beat.speaker_id) if beat.speaker_id else None,
                state_delta_json=beat.state_delta,
                created_at=beat.created_at,
                updated_at=beat.updated_at,
            )
        )
        return beat

    def get(self, beat_id: BeatId) -> Beat | None:
        row = self._session.get(BeatRow, str(beat_id))
        if not row:
            return None
        emo = row.emotion_json or {}
        return Beat(
            id=BeatId(row.id),
            scene_id=SceneId(row.scene_id),
            seq=row.seq,
            intent=row.intent,
            subtext=row.subtext,
            emotion=EmotionSpec(name=emo.get("name", "neutral"), intensity=float(emo.get("intensity", 0.5))),
            action=row.action,
            speaker_id=CharacterId(row.speaker_id) if row.speaker_id else None,
            state_delta=dict(row.state_delta_json or {}),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def list_for_scene(self, scene_id: SceneId) -> list[Beat]:
        rows = self._session.scalars(
            select(BeatRow).where(BeatRow.scene_id == str(scene_id)).order_by(BeatRow.seq.asc())
        ).all()
        return [self.get(BeatId(r.id)) for r in rows]  # type: ignore[misc]


class SqlAlchemyScriptEventRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, event: ScriptEvent) -> ScriptEvent:
        self._session.add(self._to_row(event))
        return event

    def get(self, event_id: ScriptEventId) -> ScriptEvent | None:
        row = self._session.get(ScriptEventRow, str(event_id))
        return self._from_row(row) if row else None

    def list_for_beat(self, beat_id: BeatId) -> list[ScriptEvent]:
        rows = self._session.scalars(
            select(ScriptEventRow)
            .where(ScriptEventRow.beat_id == str(beat_id))
            .order_by(ScriptEventRow.created_at.asc())
        ).all()
        return [self._from_row(r) for r in rows]

    def save(self, event: ScriptEvent) -> ScriptEvent:
        row = self._session.get(ScriptEventRow, str(event.id))
        if row is None:
            return self.add(event)
        fresh = self._to_row(event)
        for col in (
            "kind",
            "speaker_id",
            "text",
            "status",
            "locked",
            "revision",
            "tone",
            "critic_scores_json",
            "director_plan_json",
            "updated_at",
        ):
            setattr(row, col, getattr(fresh, col))
        return event

    def _to_row(self, event: ScriptEvent) -> ScriptEventRow:
        return ScriptEventRow(
            id=str(event.id),
            beat_id=str(event.beat_id),
            kind=event.kind.value,
            speaker_id=str(event.speaker_id) if event.speaker_id else None,
            text=event.text,
            status=event.status.value,
            locked=event.locked,
            revision=event.revision,
            tone=event.tone,
            critic_scores_json=event.critic_scores,
            director_plan_json=event.director_plan,
            created_at=event.created_at,
            updated_at=event.updated_at,
        )

    def _from_row(self, row: ScriptEventRow) -> ScriptEvent:
        return ScriptEvent(
            id=ScriptEventId(row.id),
            beat_id=BeatId(row.beat_id),
            kind=ScriptEventKind(row.kind),
            speaker_id=CharacterId(row.speaker_id) if row.speaker_id else None,
            text=row.text,
            status=ScriptEventStatus(row.status),
            locked=row.locked,
            revision=row.revision,
            tone=row.tone,
            critic_scores=dict(row.critic_scores_json or {}),
            director_plan=dict(row.director_plan_json or {}),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )