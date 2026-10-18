from __future__ import annotations

from typing import Any

from creator_studio.application.projects.workflow import compute_workflow
from creator_studio.application.prompt.context import resolve_prompt_context
from creator_studio.domain.ids import ProjectId
from creator_studio.domain.prompt import compute_context_hash
from creator_studio.ports.unit_of_work import UnitOfWork


class ProjectDashboard:
    def __init__(self, uow: UnitOfWork, handoff: Any) -> None:
        self._uow = uow
        self._handoff = handoff

    def get(self, project_id: str) -> dict[str, Any]:
        with self._uow as uow:
            project = uow.projects.get(ProjectId(project_id))
            if project is None:
                raise ValueError("project not found")
            scenes = uow.scenes.list_for_project(ProjectId(project_id))
            beats = [b for scene in scenes for b in uow.beats.list_for_scene(scene.id)]
            shots = [shot for beat in beats for shot in uow.shots.list_for_beat(beat.id)]
            events = [event for beat in beats for event in uow.script_events.list_for_beat(beat.id)]
            tryon_sessions = [session for scene in scenes
                for session_id in scene.initial_state.get("tryon_session_ids", [])
                if (session := uow.tryon_sessions.get(session_id)) is not None]
            locked = [event for event in events if event.locked]
            locked_beat_ids = {str(event.beat_id) for event in locked}
            characters = sorted({str(b.speaker_id) for b in beats if b.speaker_id})
            next_actions: list[dict[str, str]] = []
            shot_items: list[dict[str, Any]] = []
            generations: list[dict[str, Any]] = []
            adopted: dict[str, dict[str, str]] = {}
            adopted_shot_ids: set[str] = set()
            pending_ids: set[str] = set()
            pending_reviews: list[dict[str, str]] = []
            workflow_shots: list[dict[str, Any]] = []
            for shot in shots:
                draft = uow.prompt_drafts.get(shot.current_prompt_draft_id) if shot.current_prompt_draft_id else None
                stale = bool(draft and draft.is_stale(compute_context_hash(
                    shot_revision=shot.revision, render_spec=resolve_prompt_context(uow, shot),
                    template_id=draft.template_id, template_version=draft.template_version)))
                shot_items.append({"id": str(shot.id), "beat_id": str(shot.beat_id), "revision": shot.revision,
                                   "stale_reason": shot.stale_reason, "prompt_stale": stale})
                if stale or shot.is_stale:
                    next_actions.append({"kind": "prompt_stale" if stale else "shot_stale", "shot_id": str(shot.id)})
                attempts = uow.generation_attempts.list_for_shot(shot.id)
                latest_attempt_id: str | None = None
                has_generation = False
                for attempt in attempts:
                    has_generation = True
                    latest_attempt_id = attempt.id
                    decisions: dict[str, str] = {}
                    for aid in attempt.output_asset_ids:
                        asset = uow.assets.get(aid)
                        if asset is None:
                            continue
                        decisions[aid] = asset.review_decision.value
                        if asset.review_decision.value == "adopted":
                            adopted[aid] = {"asset_id": aid, "shot_id": str(shot.id), "beat_id": str(shot.beat_id)}
                            adopted_shot_ids.add(str(shot.id))
                        elif asset.review_decision.value == "pending":
                            pending_ids.add(aid)
                    generations.append({"id": attempt.id, "shot_id": str(shot.id), "created_at": attempt.created_at.isoformat(),
                                        "output_asset_ids": attempt.output_asset_ids, "asset_decisions": decisions})
                    if "pending" in decisions.values():
                        next_actions.append({"kind": "generation_pending", "shot_id": str(shot.id), "attempt_id": attempt.id})
                        pending_reviews.append({"shot_id": str(shot.id), "attempt_id": attempt.id})
                workflow_shots.append({
                    "id": str(shot.id),
                    "beat_id": str(shot.beat_id),
                    "prompt_stale": stale,
                    "is_stale": bool(shot.is_stale),
                    "has_generation": has_generation,
                    "latest_attempt_id": latest_attempt_id,
                })
            for beat in beats:
                if not any(event.beat_id == beat.id for event in locked):
                    next_actions.append({"kind": "dialogue_unlocked", "scene_id": str(beat.scene_id), "beat_id": str(beat.id)})
            generations.sort(key=lambda item: (item["created_at"], item["id"]), reverse=True)
            latest = self._handoff.latest(project_id)
            workflow = compute_workflow(
                beats=[{"id": str(b.id), "scene_id": str(b.scene_id)} for b in beats],
                locked_beat_ids=locked_beat_ids,
                shots=workflow_shots,
                adopted_shot_ids=adopted_shot_ids,
                pending_reviews=pending_reviews,
                latest_handoff=latest,
            )
            return {"counts": {"scenes": len(scenes), "beats": len(beats), "characters": len(characters),
                               "shots": len(shots), "generations": len(generations), "adopted": len(adopted), "pending": len(pending_ids)},
                    "workflow": workflow,
                    "next_actions": next_actions, "recent_shots": shot_items, "recent_generations": generations[:12],
                    "latest_handoff": latest, "scenes": [{"id": str(s.id), "title": s.title, "objective": s.objective} for s in scenes],
                    "beats": [{"id": str(b.id), "scene_id": str(b.scene_id), "intent": b.intent, "speaker_id": b.speaker_id} for b in beats],
                    "script_events": [{"id": str(e.id), "beat_id": str(e.beat_id), "text": e.text, "locked": e.locked,
                                       "tone": e.tone, "critic_scores": e.critic_scores, "speaker_id": e.speaker_id} for e in events],
                    "tryon_sessions": [{"session_id": session.id, "character_id": str(session.character_id),
                        "outfit_profile_id": session.outfit_profile_id, "candidate_asset_ids": session.candidate_asset_ids,
                        "adopted_asset_id": session.adopted_asset_id, "status": session.status,
                        "scene_id": next(str(scene.id) for scene in scenes if session.id in scene.initial_state.get("tryon_session_ids", []))} for session in tryon_sessions],
                    "adopted_assets": list(adopted.values()), "character_ids": characters}
