from creator_studio.application.projects.context import ProjectContextQuery
from creator_studio.application.projects.create_project import CreateProjectCommand
from creator_studio.infrastructure.container import Container


def test_project_context_resolves_hierarchy(container: Container) -> None:
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

    context = ProjectContextQuery(container.uow()).get(
        project.id, shot_id=str(shot.id)
    )

    assert context["project"]["title"] == "Cafe Story"
    assert context["scene"]["title"] == "夕方のカフェ"
    assert context["beat"]["title"] == "もう少し一緒にいたい"
    assert context["shot"]["label"] == "Shot 01"
    assert context["character"]["display_name"] == "リゼ・ヘルエスタ"
    assert context["script_excerpt"] == "えへへ、まだ帰らなくてもいいですよ？"


def test_project_context_partial_without_shot(container: Container) -> None:
    project = container.create_project().execute(CreateProjectCommand(title="Partial"))
    scene = container.create_scene().execute(project.id, "Cafe")
    beat = container.create_beat().execute(scene.id, intent="stay")

    context = ProjectContextQuery(container.uow()).get(
        project.id, scene_id=str(scene.id), beat_id=str(beat.id)
    )

    assert context["project"]["title"] == "Partial"
    assert context["scene"]["title"] == "Cafe"
    assert context["beat"]["title"] == "stay"
    assert context["shot"] is None
    assert context["character"] is None
