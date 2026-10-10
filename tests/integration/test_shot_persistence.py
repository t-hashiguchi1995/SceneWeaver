from __future__ import annotations

from creator_studio.application.projects.create_project import CreateProjectCommand
from creator_studio.infrastructure.container import Container, reset_container
from creator_studio.infrastructure.db.session import reset_engine
from creator_studio.infrastructure.settings import Settings


def test_shot_survives_restart_and_generation_is_immutable(settings: Settings) -> None:
    """Script rev change stale-marks Shot/Plan only; GenerationAttempt stays; restart keeps SQL."""
    from creator_studio.infrastructure.db.migrate import upgrade_head

    upgrade_head(settings.sqlalchemy_url())
    reset_engine()
    c1 = Container(settings)

    project = c1.create_project().execute(CreateProjectCommand(title="Persist"))
    char = c1.create_character().execute("A")
    scene = c1.create_scene().execute(project.id, "S")
    beat = c1.create_beat().execute(scene.id, intent="stay", speaker_id=char.id)
    pipe = c1.shot_pipeline()
    shot = pipe.plan_shot(beat.id)
    rendered = pipe.render(shot.id, use_pose=False)
    attempt_id = rendered["generation_attempt_id"]
    plan_id = rendered["render_plan_id"]
    shot_id = shot.id
    workflow_hash = rendered["workflow_hash"]
    outputs = list(rendered["output_asset_ids"])

    attempt = pipe.get_attempt(attempt_id)
    assert attempt.status == "succeeded"
    assert attempt.based_on_shot_revision == 1
    assert attempt.workflow_hash == workflow_hash
    provenance_payload = dict(attempt.payload)

    # Script revision change → Shot + RenderPlan stale; Generation immutable
    pipe.invalidate_for_script_change(beat.id, reason="script_revision")
    stale_shot = pipe.get_shot(shot_id)
    assert stale_shot.stale_reason == "script_revision"
    stale_plan = pipe.get_plan(plan_id)
    assert stale_plan.stale_reason == "script_revision"

    attempt_after = pipe.get_attempt(attempt_id)
    assert attempt_after.status == "succeeded"
    assert attempt_after.based_on_shot_revision == 1
    assert attempt_after.workflow_hash == workflow_hash
    assert attempt_after.payload == provenance_payload
    assert attempt_after.output_asset_ids == outputs
    assert attempt_after.is_current_for(stale_shot.revision) is True

    # Simulate API process restart
    reset_container()
    reset_engine()
    c2 = Container(settings)
    pipe2 = c2.shot_pipeline()
    reloaded_shot = pipe2.get_shot(shot_id)
    reloaded_plan = pipe2.get_plan(plan_id)
    reloaded_attempt = pipe2.get_attempt(attempt_id)

    assert reloaded_shot.stale_reason == "script_revision"
    assert reloaded_plan.stale_reason == "script_revision"
    assert reloaded_attempt.status == "succeeded"
    assert reloaded_attempt.based_on_shot_revision == 1
    assert reloaded_attempt.workflow_hash == workflow_hash
    assert reloaded_attempt.payload == provenance_payload
    assert reloaded_attempt.output_asset_ids == outputs
