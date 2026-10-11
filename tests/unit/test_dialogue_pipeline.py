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

def test_locked_dialogue_and_state_reach_writer_critic_and_shot_planner(container: Container, monkeypatch) -> None:
    from creator_studio.adapters.llm import StubLLMProvider

    class RecordingStub(StubLLMProvider):
        def __init__(self):
            self.users = []

        def complete_json(self, **kwargs):
            self.users.append(kwargs['user'])
            return super().complete_json(**kwargs)

    llm = RecordingStub()
    monkeypatch.setattr(container, 'llm', lambda: llm)
    project = container.create_project().execute(CreateProjectCommand(title='Continuity'))
    character = container.create_character().execute('リゼ・ヘルエスタ')
    container.update_persona().execute(character.id, {'max_chars': 48, 'forbidden_patterns': ['わらわ']})
    scene = container.create_scene().execute(project.id, 'Library', initial_state={
        'memo_meaning': 'unknown', 'background': 'library shelves',
        'relationship': {'trust': 'high'},
    })
    first = container.create_beat().execute(scene.id, 'find memo', speaker_id=character.id, state_delta={'memo_found': True})
    pipeline = container.dialogue_pipeline()
    candidates = pipeline.generate_candidates(beat_id=first.id, character_id=character.id)
    locked_text = 'この数字は何でしょう。一緒に確かめません？'
    pipeline.lock_script_event(candidates.candidates[0].id, locked_text)
    second = container.create_beat().execute(scene.id, 'realize return date', speaker_id=character.id,
        state_delta={'memo_meaning': 'return_date', 'lighting': 'evening light'})
    result = pipeline.generate_candidates(beat_id=second.id, character_id=character.id)
    for user in llm.users[3:6]:
        assert locked_text in user
        assert '"memo_found": true' in user
        assert '"memo_meaning": "unknown"' in user
        assert '"memo_meaning": "return_date"' in user
        assert '"trust": "high"' in user
    import json
    director_context = json.loads(llm.users[3].split('Context:\n', 1)[1])
    assert [e['text'] for e in director_context['previous_locked_script_events']] == [locked_text]
    assert '48' in llm.users[5] and 'わらわ' in llm.users[5]
    second_text = '返却日でしたね。間に合ってよかったです。'
    pipeline.lock_script_event(result.candidates[0].id, second_text)
    shot = container.shot_pipeline().plan_shot(second.id)
    assert second_text in llm.users[-1]
    assert '"memo_meaning": "return_date"' in llm.users[-1]
    container.shot_pipeline().update_shot(shot.id, {'prompt_profile_id': 'anima_story_panel'})
    draft = container.prompt_draft_service().ensure_for_shot(shot.id)
    assert 'evening light' in draft.rendered_base_positive
    assert 'library shelves' in draft.rendered_base_positive
