from __future__ import annotations

import pytest

from creator_studio.application.projects.create_project import CreateProjectCommand
from creator_studio.infrastructure.container import Container


def test_stub_dialogue_pipeline_and_lock(container: Container) -> None:
    project = container.create_project().execute(CreateProjectCommand(title="Story Demo"))
    character = container.create_character().execute("リゼヘル")
    container.update_persona().execute(
        character.id,
        {
            "first_person": "私",
            "second_person": "あなた",
            "voice_examples": [
                {"text": "えへへ、もっと褒めてもいいんですよ？", "tags": ["soft"], "polarity": "positive"},
                {"text": "じゃあ、一緒に行きません？", "tags": ["invite"], "polarity": "positive"},
            ],
        },
    )
    # tryon_base remains null — Character create must succeed
    assert character.visual_identity["tryon_base_asset_id"] is None

    scene = container.create_scene().execute(project.id, "Cafe", objective="stay together")
    beat = container.create_beat().execute(
        scene.id,
        intent="もう少し一緒にいたい",
        subtext="直接寂しいとは言わない",
        emotion={"name": "shy", "intensity": 0.65},
        speaker_id=character.id,
    )

    result = container.dialogue_pipeline().generate_candidates(
        beat_id=beat.id,
        character_id=character.id,
    )
    assert result.director_plan["intent"]
    assert len(result.candidates) == 3
    assert result.voice_examples
    assert result.candidates[0].critic_scores.get("character_fidelity") == 4.7

    locked = container.dialogue_pipeline().lock_script_event(
        result.candidates[0].id,
        text="……もう少しだけ、付き合ってくれません？",
    )
    assert locked.locked is True

    with pytest.raises(PermissionError):
        container.dialogue_pipeline().update_locked_forbidden(str(locked.id), "書き換え禁止")

    with pytest.raises(PermissionError):
        container.dialogue_pipeline().generate_candidates(
            beat_id=beat.id,
            character_id=character.id,
        )