from __future__ import annotations

from creator_studio.application.projects.create_project import CreateProjectCommand
from creator_studio.infrastructure.container import Container


def test_list_attempts_exposes_immutable_prompt_snapshot(container: Container) -> None:
    project = container.create_project().execute(CreateProjectCommand(title="Review"))
    scene = container.create_scene().execute(project_id=project.id, title="Cafe", objective="stay")
    beat = container.create_beat().execute(scene_id=scene.id, intent="smile", action="look")
    pipe = container.shot_pipeline()
    shot = pipe.plan_shot(beat.id)
    drafts = container.prompt_draft_service()
    view = drafts.ensure_for_shot(shot.id)
    drafts.update_edits(shot.id, view.edited_positive + ", review_marker", view.edited_negative)

    first = pipe.render(shot.id, use_pose=False)
    second = pipe.render(shot.id, use_pose=False)

    items = pipe.list_attempts_for_shot(shot.id)
    assert len(items) >= 2
    assert items[0]["id"] == second["generation_attempt_id"]
    assert items[1]["id"] == first["generation_attempt_id"]
    assert "review_marker" in str(items[0]["final_positive_prompt"])
    assert items[0]["prompt_hash"]
    assert items[0]["seed"] is not None

    drafts.update_edits(shot.id, "mutated_after", "neg")
    reloaded = pipe.list_attempts_for_shot(shot.id)
    assert reloaded[1]["final_positive_prompt"] == items[1]["final_positive_prompt"]
    assert "mutated_after" not in str(reloaded[1]["final_positive_prompt"])
