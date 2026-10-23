from __future__ import annotations

from typing import Any

from creator_studio.domain.ids import ProjectId
from creator_studio.domain.story import resolve_effective_state
from creator_studio.ports.unit_of_work import UnitOfWork


class ProjectContextQuery:
    """Read model for creator production screens (Story / Studio / Review / …)."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def get(
        self,
        project_id: str,
        *,
        scene_id: str | None = None,
        beat_id: str | None = None,
        shot_id: str | None = None,
    ) -> dict[str, Any]:
        with self._uow as uow:
            project = uow.projects.get(ProjectId(project_id))
            if project is None:
                raise ValueError("project not found")

            shot = uow.shots.get(shot_id) if shot_id else None
            if shot_id and shot is None:
                raise ValueError("shot not found")

            resolved_beat_id = str(shot.beat_id) if shot else beat_id
            beat = uow.beats.get(resolved_beat_id) if resolved_beat_id else None
            if resolved_beat_id and beat is None:
                raise ValueError("beat not found")

            resolved_scene_id = str(beat.scene_id) if beat else scene_id
            scene = uow.scenes.get(resolved_scene_id) if resolved_scene_id else None
            if resolved_scene_id and scene is None:
                raise ValueError("scene not found")

            if scene is not None and str(scene.project_id) != project_id:
                raise ValueError("scene does not belong to project")
            if beat is not None and scene is not None and str(beat.scene_id) != str(scene.id):
                raise ValueError("beat does not belong to scene")
            if shot is not None and beat is not None and str(shot.beat_id) != str(beat.id):
                raise ValueError("shot does not belong to beat")

            character_payload = None
            outfit_payload = None
            script_excerpt = None
            shot_payload = None

            if shot is not None and beat is not None:
                siblings = sorted(
                    uow.shots.list_for_beat(beat.id),
                    key=lambda item: (item.created_at, str(item.id)),
                )
                index = next(
                    (i for i, item in enumerate(siblings, start=1) if str(item.id) == str(shot.id)),
                    1,
                )
                shot_payload = {
                    "id": str(shot.id),
                    "label": f"Shot {index:02d}",
                    "index": index,
                }

            if beat is not None:
                events = uow.script_events.list_for_beat(beat.id)
                locked = next((event for event in events if event.locked), None)
                chosen = locked or (events[0] if events else None)
                if chosen is not None and chosen.text:
                    script_excerpt = chosen.text

                character_id = None
                if shot is not None:
                    character_id = shot.render_spec.get("character_id")
                character_id = character_id or beat.speaker_id
                if character_id:
                    character = uow.characters.get(character_id)
                    if character is not None:
                        character_payload = {
                            "id": str(character.id),
                            "display_name": character.display_name,
                        }

                outfit_id = None
                if shot is not None:
                    outfit_id = shot.render_spec.get("outfit_profile_id")
                if scene is not None and not outfit_id:
                    state = resolve_effective_state(
                        scene.initial_state,
                        [
                            b.state_delta
                            for b in sorted(uow.beats.list_for_scene(scene.id), key=lambda b: b.seq)
                            if b.seq <= beat.seq
                        ],
                    )
                    outfit_id = state.get("outfit_profile_id")
                if outfit_id:
                    outfit = uow.outfit_profiles.get(str(outfit_id))
                    if outfit is not None:
                        outfit_payload = {
                            "id": outfit.id,
                            "label": outfit.title,
                        }

            return {
                "project": {
                    "id": str(project.id),
                    "title": project.title,
                },
                "scene": (
                    {"id": str(scene.id), "title": scene.title} if scene is not None else None
                ),
                "beat": (
                    {"id": str(beat.id), "title": beat.intent} if beat is not None else None
                ),
                "shot": shot_payload,
                "character": character_payload,
                "outfit": outfit_payload,
                "script_excerpt": script_excerpt,
            }
