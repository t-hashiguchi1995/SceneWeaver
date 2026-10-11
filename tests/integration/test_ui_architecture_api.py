from fastapi.testclient import TestClient

from apps.api.deps import container as container_dep
from apps.api.main import app
from creator_studio.application.projects.create_project import CreateProjectCommand


def test_content_replay_dashboard_settings_and_assembly(container, tmp_path):
    project = container.create_project().execute(CreateProjectCommand(title='Architecture'))
    character = container.create_character().execute('A')
    scene = container.create_scene().execute(project.id, 'Studio')
    beat = container.create_beat().execute(scene.id, intent='stay', speaker_id=character.id)
    shot = container.shot_pipeline().plan_shot(beat.id)
    app.dependency_overrides[container_dep] = lambda: container
    try:
        with TestClient(app) as client:
            rendered = client.post(f'/api/v1/shots/{shot.id}/render', json={'seed': 42, 'use_pose': False}).json()
            aid = rendered['output_asset_ids'][0]
            content = client.get(f'/api/v1/assets/{aid}/content')
            assert content.status_code == 200 and content.headers['content-type'] == 'image/png'
            assert content.content.startswith(b'\x89PNG')
            assert client.get(f'/api/v1/assets/{aid}/content', headers={'If-None-Match': content.headers['etag']}).status_code == 304
            assert client.get('/api/v1/assets/missing/content').status_code == 404
            attempt_id = rendered['generation_attempt_id']
            original = client.get(f'/api/v1/generations/{attempt_id}').json()
            client.put(f'/api/v1/shots/{shot.id}', json={'expression': {'id': 'smile'}, 'control_strength': 0.2})
            replay = client.post(f'/api/v1/generations/{attempt_id}/replay', json={'seed_mode': 'same'})
            assert replay.status_code == 200, replay.text
            replay_detail = client.get(f"/api/v1/generations/{replay.json()['generation_attempt_id']}").json()
            assert replay_detail['seed'] == 42
            assert replay_detail['payload']['render_snapshot']['slots'] == original['payload']['render_snapshot']['slots']
            assert replay_detail['payload']['capability'] == 'BaseRender'
            new = client.post(f'/api/v1/generations/{attempt_id}/replay', json={'seed_mode': 'new'}).json()
            assert client.get(f"/api/v1/generations/{new['generation_attempt_id']}").json()['seed'] != 42
            assert client.get(f'/api/v1/generations/{attempt_id}').json() == original
            client.put(f'/api/v1/shots/{shot.id}/prompt-draft', json={'edited_positive': 'edited historical prompt', 'edited_negative': 'negative'})
            edited = client.post(f'/api/v1/shots/{shot.id}/render', json={'source_attempt_id': attempt_id, 'seed': 44})
            assert edited.status_code == 200, edited.text
            edited_detail = client.get(f"/api/v1/generations/{edited.json()['generation_attempt_id']}").json()
            assert edited_detail['seed'] == 44 and edited_detail['payload']['capability'] == 'BaseRender'
            assert edited_detail['final_positive_prompt'] == 'edited historical prompt'
            client.put(f'/api/v1/assets/{aid}/decision', json={'decision': 'adopted'})
            dashboard = client.get(f'/api/v1/projects/{project.id}/dashboard').json()
            assert dashboard['counts']['shots'] == 1 and dashboard['counts']['adopted'] == 1
            assert dashboard['adopted_assets'][0]['asset_id'] == aid
            out = tmp_path / 'csp-output'
            assert client.put('/api/v1/settings', json={'csp_export_dir': str(out)}).status_code == 200
            result = client.post('/api/v1/csp/handoffs', json={'project_id': project.id, 'pages': [{'page_no': 1, 'panels': [{'panel_no': 1, 'shot_id': shot.id, 'asset_id': aid, 'script_event_ids': []}]}], 'script_rows': []})
            assert result.status_code == 200, result.text
            assert result.json()['path'].startswith(str(out))
            previous_backend = container.image_backend()
            container.settings_service().update({'image_backend': 'comfy_dry', 'comfy_url': 'http://127.0.0.1:8188'})
            assert container.image_backend() is not previous_backend
            container.settings_service().update({'image_backend': 'fake'})
            client.put(f'/api/v1/shots/{shot.id}', json={'prompt_profile_id': 'anima_story_panel'})
            draft = client.post(f'/api/v1/shots/{shot.id}/prompt-draft').json()
            assert draft['assembly_metadata']['component_refs']
            generated = client.post(f'/api/v1/shots/{shot.id}/render', json={'use_pose': False})
            assert generated.status_code == 200, generated.text
            detail = client.get(f"/api/v1/generations/{generated.json()['generation_attempt_id']}").json()
            assert detail['payload']['prompt_profile_id'] == 'anima_story_panel'
            client.put(f'/api/v1/characters/{character.id}/visual-identity', json={'hair': 'blue hair'})
            assert client.get(f'/api/v1/shots/{shot.id}/prompt-draft').json()['stale'] is True
            assert client.get(f"/api/v1/generations/{generated.json()['generation_attempt_id']}").json() == detail
    finally:
        app.dependency_overrides.clear()
