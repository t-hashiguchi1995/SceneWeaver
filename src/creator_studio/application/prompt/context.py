from __future__ import annotations

from copy import deepcopy
import re
from typing import Any

from creator_studio.domain.story import resolve_effective_state
from creator_studio.ports.unit_of_work import UnitOfWork


def resolve_legacy_choices(fragment: str) -> str:
    """Choose the first legacy wildcard branch deterministically; never execute macros."""
    pattern = re.compile(r"\{([^{}]*)\}")
    while pattern.search(fragment):
        fragment = pattern.sub(lambda match: match[1].split("|", 1)[0].strip(), fragment)
    return fragment


def resolve_prompt_context(uow: UnitOfWork, shot: Any) -> dict[str, Any]:
    spec = deepcopy(shot.render_spec)

    # Character / outfit / scene state always resolve — ownership must not depend on
    # prompt_profile_id (Anima profile assembly is optional).
    beat = uow.beats.get(shot.beat_id)
    scene = uow.scenes.get(beat.scene_id) if beat else None
    state = (
        resolve_effective_state(
            scene.initial_state,
            [
                b.state_delta
                for b in sorted(uow.beats.list_for_scene(scene.id), key=lambda b: b.seq)
                if beat and b.seq <= beat.seq
            ],
        )
        if scene
        else {}
    )
    character_id = spec.get("character_id") or (beat.speaker_id if beat else None)
    character = uow.characters.get(character_id) if character_id else None
    if character:
        visual = character.visual_identity
        spec.setdefault("identity_tags", visual.identity_tags)
        spec.setdefault(
            "character_traits",
            ", ".join(filter(None, [visual.hair, visual.eyes, visual.body])),
        )
        if visual.character_name:
            spec.setdefault("character_name", visual.character_name)
        if visual.franchise:
            spec.setdefault("franchise", visual.franchise)
        if visual.body_tags:
            spec.setdefault("body_tags", list(visual.body_tags))
        # Gate 2.6 adopted Anima prompt — optional override when present and
        # shot has not already set a custom base via render_spec.
        if visual.saved_anima_positive and not spec.get("_ignore_saved_anima_positive"):
            spec.setdefault("_saved_anima_positive", visual.saved_anima_positive)
        spec["_character_revision"] = character.updated_at.isoformat()
        spec.setdefault("character_id", str(character.id))
    if scene:
        spec.setdefault("background", state.get("background", scene.title))
        if state.get("lighting"):
            spec.setdefault("lighting", state["lighting"])
        if state.get("outfit_tags"):
            spec.setdefault("outfit_tags", state["outfit_tags"])
        spec["_effective_scene_state"] = state
        spec["_scene_revision"] = scene.updated_at.isoformat()
        project = uow.projects.get(scene.project_id)
        if project is not None:
            spec.setdefault("content_rating", project.content_rating)
    outfit_id = spec.get("outfit_profile_id") or state.get("outfit_profile_id")
    outfit = uow.outfit_profiles.get(outfit_id) if outfit_id else None
    if outfit:
        # Prevent silent cross-character outfit attachment (multi-char SceneWeaver).
        if outfit.character_id is not None:
            selected_id = str(character.id) if character is not None else None
            if selected_id is None or selected_id != str(outfit.character_id):
                raise ValueError("outfit does not belong to selected character")
        spec.setdefault(
            "outfit_tags",
            outfit.semantic.get("garment_description", outfit.title),
        )
        spec.setdefault("outfit_profile_id", outfit.id)
        spec["_outfit_revision"] = outfit.updated_at.isoformat()
        spec["_outfit_character_id"] = (
            str(outfit.character_id) if outfit.character_id else None
        )

    if not spec.get("prompt_profile_id"):
        return spec

    presets = uow.prompt_presets.list_enabled()
    selected = set(spec.get("prompt_preset_ids") or [])
    known = {p.id for p in presets}
    if selected - known:
        raise ValueError("selected prompt preset is missing or disabled")
    components = list(spec.get("prompt_components") or [])
    aliases = {
        "costume": "outfit",
        "location": "background",
        "expressions": "expression",
        "poses": "pose",
        "accessory": "outfit",
        "shoes": "outfit",
    }
    for preset in presets:
        is_default = (
            preset.source_file == "dynamic/lighting_default.yaml"
            and preset.label == "soft_indoor"
        )
        if preset.id not in selected and not is_default:
            continue
        category = preset.category or preset.kind
        kind = aliases.get(category.split("_")[0], category.split("_")[0])
        if kind not in {
            "outfit",
            "background",
            "expression",
            "pose",
            "camera",
            "lighting",
            "style",
            "quality",
        }:
            kind = "user_additions"
        components.append(
            {
                "component_id": preset.id,
                "kind": kind,
                "text": resolve_legacy_choices(preset.prompt_fragment),
                "component_version": preset.content_hash,
                "content_rating": preset.content_rating,
                "precedence": 3 if preset.id in selected else 1,
                "subkind": "emotion" if kind == "expression" else "",
                "model_scope": "any",
            }
        )
    spec["prompt_components"] = components
    return spec
