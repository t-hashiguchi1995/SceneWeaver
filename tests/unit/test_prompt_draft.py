from __future__ import annotations

import pytest

from creator_studio.application.projects.create_project import CreateProjectCommand
from creator_studio.application.prompt.renderer import PromptRenderer
from creator_studio.domain.prompt import compute_prompt_hash
from creator_studio.infrastructure.container import Container


def test_prompt_hash_uses_nul_separator() -> None:
    a = compute_prompt_hash("foo", "bar")
    b = compute_prompt_hash("fo", "obar")
    assert a != b
    assert len(a) == 64


def test_prompt_draft_stale_reset_rebuild_and_attempt_snapshot(container: Container) -> None:
    project = container.create_project().execute(CreateProjectCommand(title="Prompt Draft Project"))
    scene = container.create_scene().execute(project_id=project.id, title="Cafe", objective="stay")
    beat = container.create_beat().execute(scene_id=scene.id, intent="smile", action="look")
    pipe = container.shot_pipeline()
    shot = pipe.plan_shot(beat.id)

    drafts = container.prompt_draft_service()
    view = drafts.ensure_for_shot(shot.id)
    assert view.modified is False
    assert view.stale is False
    assert view.rendered_base_positive

    edited = drafts.update_edits(
        shot.id,
        view.edited_positive + ", soft smile bar_marker",
        view.edited_negative,
    )
    assert edited.modified is True
    assert "bar_marker" in edited.edited_positive

    rendered = pipe.render(shot.id, use_pose=False)
    attempt = pipe.get_attempt(rendered["generation_attempt_id"])
    snap = attempt.payload["final_positive_prompt"]
    assert "bar_marker" in snap
    assert attempt.payload["prompt_hash"] == compute_prompt_hash(
        snap, attempt.payload["final_negative_prompt"]
    )

    drafts.update_edits(shot.id, edited.edited_positive + ", later_edit", edited.edited_negative)
    reloaded = pipe.get_attempt(rendered["generation_attempt_id"])
    assert reloaded.payload["final_positive_prompt"] == snap

    reset = drafts.reset_edits(shot.id)
    assert reset.modified is False
    assert reset.edited_positive == reset.rendered_base_positive

    pipe.update_shot(shot.id, {"expression": {"id": "shy", "intensity": 0.8}})
    stale_view = drafts.get_for_shot(shot.id)
    assert stale_view.stale is True

    # After reset_edits, draft is not modified — rebuild without confirm is OK
    rebuilt = drafts.rebuild(shot.id)
    assert rebuilt.stale is False
    assert "shy" in rebuilt.rendered_base_positive

    edited_again = drafts.update_edits(
        shot.id, rebuilt.edited_positive + ", keep_me", rebuilt.edited_negative
    )
    assert edited_again.modified is True
    with pytest.raises(ValueError, match="confirm"):
        drafts.rebuild(shot.id)
    confirmed = drafts.rebuild(shot.id, confirm=True)
    assert confirmed.modified is False
    assert "keep_me" not in confirmed.edited_positive


def test_renderer_source_description_matches_compiler() -> None:
    renderer = PromptRenderer()
    rendered = renderer.render_anima({"identity_tags": ["1girl"], "expression": {"id": "neutral"}})
    body = renderer.describe_source(rendered.source_kind, rendered.source_ref)
    assert rendered.source_kind == "compiler_rule"
    assert "Anima Compiler v1" in body
    assert rendered.positive
    assert rendered.negative
