from fastapi.testclient import TestClient

from apps.api.deps import container as container_dep
from apps.api.main import app
from creator_studio.application.projects.create_project import CreateProjectCommand


def test_project_context_endpoint(container) -> None:
    project = container.create_project().execute(CreateProjectCommand(title="Cafe Story"))
    character = container.create_character().execute("リゼ・ヘルエスタ")
    scene = container.create_scene().execute(project.id, "夕方のカフェ")
    beat = container.create_beat().execute(
        scene.id, intent="もう少し一緒にいたい", speaker_id=character.id
    )
    dialogue = container.dialogue_pipeline().generate_candidates(
        beat_id=beat.id, character_id=character.id
    )
    container.dialogue_pipeline().lock_script_event(
        dialogue.candidates[0].id, text="えへへ、まだ帰らなくてもいいですよ？"
    )
    shot = container.shot_pipeline().plan_shot(beat.id)

    app.dependency_overrides[container_dep] = lambda: container
    try:
        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/projects/{project.id}/context",
                params={"shot_id": str(shot.id)},
            )
            assert response.status_code == 200
            body = response.json()
            assert body["project"]["title"] == "Cafe Story"
            assert body["scene"]["title"] == "夕方のカフェ"
            assert body["beat"]["title"] == "もう少し一緒にいたい"
            assert body["shot"]["label"] == "Shot 01"
            assert body["character"]["display_name"] == "リゼ・ヘルエスタ"
            assert body["script_excerpt"] == "えへへ、まだ帰らなくてもいいですよ？"
    finally:
        app.dependency_overrides.pop(container_dep, None)
