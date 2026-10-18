"""Project workflow progress and semantic primary_next (CE-1).

UI labels and routes stay in the frontend; this module returns meaning only.
"""

from __future__ import annotations

from typing import Any, Literal

PrimaryNextKind = Literal[
    "create_story",
    "continue_story",
    "choose_outfit",
    "configure_shot",
    "review_generation",
    "create_csp_handoff",
    "prepare_release",
    "complete",
]


def compute_workflow(
    *,
    beats: list[dict[str, Any]],
    locked_beat_ids: set[str],
    shots: list[dict[str, Any]],
    adopted_shot_ids: set[str],
    pending_reviews: list[dict[str, str]],
    latest_handoff: dict[str, Any] | None,
) -> dict[str, Any]:
    """Compute workflow summary.

    Story done = beats with >= 1 locked ScriptEvent (not locked-event count).
    Shots done = shots with >= 1 adopted asset (not adopted-asset count).
    Release done is always null until Release Edition persistence exists.
    """
    story_total = len(beats)
    story_done = sum(1 for beat in beats if str(beat["id"]) in locked_beat_ids)
    shots_total = len(shots)
    shots_done = sum(1 for shot in shots if str(shot["id"]) in adopted_shot_ids)
    handoff_ready = latest_handoff is not None

    primary = _primary_next(
        beats=beats,
        locked_beat_ids=locked_beat_ids,
        shots=shots,
        adopted_shot_ids=adopted_shot_ids,
        pending_reviews=pending_reviews,
        handoff_ready=handoff_ready,
    )

    return {
        "story": {"done": story_done, "total": story_total},
        "shots": {"done": shots_done, "total": shots_total},
        "csp": {"ready": handoff_ready, "done": handoff_ready},
        "release": {"ready": handoff_ready, "done": None},
        "primary_next": primary,
    }


def _primary_next(
    *,
    beats: list[dict[str, Any]],
    locked_beat_ids: set[str],
    shots: list[dict[str, Any]],
    adopted_shot_ids: set[str],
    pending_reviews: list[dict[str, str]],
    handoff_ready: bool,
) -> dict[str, Any]:
    if not beats:
        return {"kind": "create_story"}

    for beat in beats:
        beat_id = str(beat["id"])
        if beat_id not in locked_beat_ids:
            return {
                "kind": "continue_story",
                "scene_id": str(beat["scene_id"]),
                "beat_id": beat_id,
            }

    shots_by_beat = {str(shot["beat_id"]): shot for shot in shots}
    for beat in beats:
        beat_id = str(beat["id"])
        if beat_id not in shots_by_beat:
            return {
                "kind": "configure_shot",
                "scene_id": str(beat["scene_id"]),
                "beat_id": beat_id,
            }

    for shot in shots:
        if shot.get("prompt_stale") or shot.get("is_stale"):
            return {"kind": "configure_shot", "shot_id": str(shot["id"])}

    if pending_reviews:
        pending = pending_reviews[0]
        return {
            "kind": "review_generation",
            "shot_id": pending["shot_id"],
            "attempt_id": pending["attempt_id"],
        }

    for shot in shots:
        shot_id = str(shot["id"])
        if shot_id not in adopted_shot_ids:
            # Prefer review when candidates exist; otherwise configure/re-render.
            if shot.get("has_generation"):
                attempt_id = shot.get("latest_attempt_id")
                next_action: dict[str, Any] = {"kind": "review_generation", "shot_id": shot_id}
                if attempt_id:
                    next_action["attempt_id"] = str(attempt_id)
                return next_action
            return {"kind": "configure_shot", "shot_id": shot_id}

    if adopted_shot_ids and not handoff_ready:
        return {"kind": "create_csp_handoff"}

    if handoff_ready:
        return {"kind": "prepare_release"}

    return {"kind": "complete"}
