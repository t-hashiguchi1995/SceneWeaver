from pathlib import Path

from fastapi.testclient import TestClient

from apps.api.deps import container as container_dep
from apps.api.main import app
from creator_studio.application.projects.create_project import CreateProjectCommand
from scripts.import_legacy_prompts import apply_plan, build_plan, reconcile_idempotency


def test_imported_library_builds_defaults_and_tracks_versions(container, tmp_path: Path):
    root = tmp_path / 'prompts' / 'dynamic'
    root.mkdir(parents=True)
    (root / 'lighting_default.yaml').write_text('categories:\n  lighting:\n    - name: soft_indoor\n      prompt: warm light, gentle shadows\n')
    (root / 'sfw_cafe.yaml').write_text('categories:\n  location_cafe_sfw:\n    - name: window\n      prompt: window seat cafe, peaceful\n')
    apply_plan(reconcile_idempotency(build_plan(root.parent), container), container)
    project = container.create_project().execute(CreateProjectCommand(title='Library'))
    character = container.create_character().execute('Original')
    scene = container.create_scene().execute(project.id, 'Cafe')
    beat = container.create_beat().execute(scene.id, intent='coffee', speaker_id=character.id)
    shot = container.shot_pipeline().plan_shot(beat.id)
    assert shot.render_spec['prompt_profile_id'] == 'anima_story_panel'
    app.dependency_overrides[container_dep] = lambda: container
    try:
        with TestClient(app) as client:
            library = client.get('/api/v1/prompt-library').json()
            preset = next(p for p in library if p['label'] == 'window')
            client.put(f'/api/v1/shots/{shot.id}', json={'prompt_preset_ids': [preset['id']]})
            draft = client.post(f'/api/v1/shots/{shot.id}/prompt-draft').json()
            assert 'window seat cafe' in draft['rendered_base_positive']
            assert 'gentle shadows' in draft['rendered_base_positive']
            assert f"{preset['id']}@{preset['version']}" in draft['assembly_metadata']['component_refs']
            rendered = client.post(f'/api/v1/shots/{shot.id}/render', json={'seed': 12})
            assert rendered.status_code == 200, rendered.text
            attempt = client.get(f"/api/v1/generations/{rendered.json()['generation_attempt_id']}").json()
            assert 'window seat cafe' in attempt['final_positive_prompt']
            client.put(f'/api/v1/shots/{shot.id}', json={'prompt_preset_ids': ['missing']})
            assert client.post(f'/api/v1/shots/{shot.id}/prompt-draft').status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_legacy_choices_are_deterministic_and_nested():
    from creator_studio.application.prompt.context import resolve_legacy_choices
    assert resolve_legacy_choices('cheerleader, {blue | white} skirt, {{smile | grin} | neutral}') == 'cheerleader, blue skirt, smile'
    assert resolve_legacy_choices('{glasses | }') == 'glasses'
    assert resolve_legacy_choices('cozy cafe') == 'cozy cafe'


def test_sampling_snapshots_preserve_edits_and_replay(container):
    import pytest
    from creator_studio.application.prompt.assembly import build_default_prompt, components_from_context
    from creator_studio.domain.prompt.assembly import PromptAssemblyProfile

    profile = PromptAssemblyProfile()
    basic = build_default_prompt(components_from_context({}), profile)
    legacy = build_default_prompt(components_from_context({'prompt_quality_profile_id': 'anima_legacy_v1'}), profile)
    assert 'score_9' not in basic.positive
    assert all(tag in legacy.positive for tag in ['year 2025', 'newest', 'score_9', 'score_8', '@fuzichoco', '@rella'])
    project = container.create_project().execute(CreateProjectCommand(title='Sampling'))
    character = container.create_character().execute('リゼ')
    scene = container.create_scene().execute(project.id, 'Prompt comparison')
    beat = container.create_beat().execute(scene.id, intent='quality', speaker_id=character.id)
    pipe = container.shot_pipeline()
    shot = pipe.plan_shot(beat.id)
    with pytest.raises(ValueError, match='sampling_steps'):
        pipe.update_shot(shot.id, {'sampling_steps': 0})
    with pytest.raises(ValueError, match='sampling_cfg'):
        pipe.update_shot(shot.id, {'sampling_cfg': float('nan')})
    pipe.update_shot(shot.id, {'sampling_steps': 24, 'sampling_cfg': 4})
    container.prompt_draft_service().ensure_for_shot(shot.id)
    user_prompt = (Path(__file__).parents[1] / 'fixtures/story/rize_user_prompt.txt').read_text().rstrip('\n')
    container.prompt_draft_service().update_edits(shot.id, user_prompt, 'fixed negative')
    result = pipe.render(shot.id, seed=77)
    attempt = pipe.get_attempt(result['generation_attempt_id'])
    assert attempt.payload['final_positive_prompt'] == user_prompt
    assert attempt.payload['render_snapshot']['slots']['sampling_steps'] == 24
    pipe.update_shot(shot.id, {'sampling_steps': 8})
    replay = pipe.replay(attempt.id, seed_mode='same')
    replayed = pipe.get_attempt(replay['generation_attempt_id'])
    assert replayed.payload['render_snapshot']['slots']['sampling_steps'] == 24
    assert replayed.payload['final_positive_prompt'] == user_prompt
