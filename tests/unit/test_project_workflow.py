from __future__ import annotations

from creator_studio.application.csp.handoff import PagePlan, PanelSlot
from creator_studio.application.projects.create_project import CreateProjectCommand
from creator_studio.application.projects.dashboard import ProjectDashboard
from creator_studio.application.projects.workflow import compute_workflow
from creator_studio.infrastructure.container import Container


def test_compute_workflow_priority_create_story() -> None:
    workflow = compute_workflow(
        beats=[],
        locked_beat_ids=set(),
        shots=[],
        adopted_shot_ids=set(),
        pending_reviews=[],
        latest_handoff=None,
    )
    assert workflow["story"] == {"done": 0, "total": 0}
    assert workflow["primary_next"]["kind"] == "create_story"
    assert workflow["release"]["done"] is None


def test_compute_workflow_continue_story() -> None:
    workflow = compute_workflow(
        beats=[{"id": "b1", "scene_id": "s1"}],
        locked_beat_ids=set(),
        shots=[],
        adopted_shot_ids=set(),
        pending_reviews=[],
        latest_handoff=None,
    )
    assert workflow["primary_next"] == {
        "kind": "continue_story",
        "scene_id": "s1",
        "beat_id": "b1",
    }


def test_compute_workflow_story_done_counts_beats_not_events() -> None:
    workflow = compute_workflow(
        beats=[{"id": "b1", "scene_id": "s1"}, {"id": "b2", "scene_id": "s1"}],
        locked_beat_ids={"b1"},
        shots=[],
        adopted_shot_ids=set(),
        pending_reviews=[],
        latest_handoff=None,
    )
    assert workflow["story"] == {"done": 1, "total": 2}


def test_compute_workflow_configure_shot_when_locked_without_shot() -> None:
    workflow = compute_workflow(
        beats=[{"id": "b1", "scene_id": "s1"}],
        locked_beat_ids={"b1"},
        shots=[],
        adopted_shot_ids=set(),
        pending_reviews=[],
        latest_handoff=None,
    )
    assert workflow["primary_next"]["kind"] == "configure_shot"
    assert workflow["primary_next"]["beat_id"] == "b1"


def test_compute_workflow_stale_before_pending_review() -> None:
    workflow = compute_workflow(
        beats=[{"id": "b1", "scene_id": "s1"}],
        locked_beat_ids={"b1"},
        shots=[{
            "id": "sh1",
            "beat_id": "b1",
            "prompt_stale": True,
            "is_stale": False,
            "has_generation": True,
            "latest_attempt_id": "a1",
        }],
        adopted_shot_ids=set(),
        pending_reviews=[{"shot_id": "sh1", "attempt_id": "a1"}],
        latest_handoff=None,
    )
    assert workflow["primary_next"] == {"kind": "configure_shot", "shot_id": "sh1"}


def test_compute_workflow_review_generation() -> None:
    workflow = compute_workflow(
        beats=[{"id": "b1", "scene_id": "s1"}],
        locked_beat_ids={"b1"},
        shots=[{
            "id": "sh1",
            "beat_id": "b1",
            "prompt_stale": False,
            "is_stale": False,
            "has_generation": True,
            "latest_attempt_id": "a1",
        }],
        adopted_shot_ids=set(),
        pending_reviews=[{"shot_id": "sh1", "attempt_id": "a1"}],
        latest_handoff=None,
    )
    assert workflow["primary_next"] == {
        "kind": "review_generation",
        "shot_id": "sh1",
        "attempt_id": "a1",
    }


def test_compute_workflow_shots_done_counts_shots_not_assets() -> None:
    workflow = compute_workflow(
        beats=[{"id": "b1", "scene_id": "s1"}, {"id": "b2", "scene_id": "s1"}],
        locked_beat_ids={"b1", "b2"},
        shots=[
            {"id": "sh1", "beat_id": "b1", "prompt_stale": False, "is_stale": False, "has_generation": True},
            {"id": "sh2", "beat_id": "b2", "prompt_stale": False, "is_stale": False, "has_generation": True},
        ],
        adopted_shot_ids={"sh1"},
        pending_reviews=[],
        latest_handoff=None,
    )
    assert workflow["shots"] == {"done": 1, "total": 2}
    assert workflow["primary_next"]["kind"] == "review_generation"
    assert workflow["primary_next"]["shot_id"] == "sh2"


def test_compute_workflow_create_csp_and_prepare_release() -> None:
    adopted = compute_workflow(
        beats=[{"id": "b1", "scene_id": "s1"}],
        locked_beat_ids={"b1"},
        shots=[{"id": "sh1", "beat_id": "b1", "prompt_stale": False, "is_stale": False, "has_generation": True}],
        adopted_shot_ids={"sh1"},
        pending_reviews=[],
        latest_handoff=None,
    )
    assert adopted["primary_next"]["kind"] == "create_csp_handoff"
    assert adopted["csp"] == {"ready": False, "done": False}
    assert adopted["release"] == {"ready": False, "done": None}

    with_handoff = compute_workflow(
        beats=[{"id": "b1", "scene_id": "s1"}],
        locked_beat_ids={"b1"},
        shots=[{"id": "sh1", "beat_id": "b1", "prompt_stale": False, "is_stale": False, "has_generation": True}],
        adopted_shot_ids={"sh1"},
        pending_reviews=[],
        latest_handoff={"revision": "r001"},
    )
    assert with_handoff["primary_next"]["kind"] == "prepare_release"
    assert with_handoff["csp"] == {"ready": True, "done": True}
    assert with_handoff["release"] == {"ready": True, "done": None}


def test_dashboard_workflow_state_transitions(container: Container) -> None:
    project = container.create_project().execute(CreateProjectCommand(title="Workflow"))
    character = container.create_character().execute("リゼヘル")
    dashboard = ProjectDashboard(container.uow(), container.csp_handoff())

    empty = dashboard.get(project.id)
    assert empty["workflow"]["primary_next"]["kind"] == "create_story"

    scene = container.create_scene().execute(project.id, "Cafe")
    beat = container.create_beat().execute(scene.id, intent="stay", speaker_id=character.id)
    unlocked = dashboard.get(project.id)
    assert unlocked["workflow"]["primary_next"]["kind"] == "continue_story"
    assert unlocked["workflow"]["primary_next"]["beat_id"] == str(beat.id)
    assert unlocked["workflow"]["story"] == {"done": 0, "total": 1}

    dialogue = container.dialogue_pipeline().generate_candidates(beat_id=beat.id, character_id=character.id)
    container.dialogue_pipeline().lock_script_event(dialogue.candidates[0].id, text="もう少し一緒にいたい")
    locked = dashboard.get(project.id)
    assert locked["workflow"]["story"] == {"done": 1, "total": 1}
    assert locked["workflow"]["primary_next"]["kind"] == "configure_shot"

    shot = container.shot_pipeline().plan_shot(beat.id)
    rendered = container.shot_pipeline().render(shot.id, use_pose=False)
    pending = dashboard.get(project.id)
    assert pending["workflow"]["primary_next"]["kind"] == "review_generation"
    assert pending["workflow"]["primary_next"]["attempt_id"] == rendered["generation_attempt_id"]

    aid = rendered["output_asset_ids"][0]
    container.set_asset_decision().execute(aid, "adopted")
    for other in rendered["output_asset_ids"][1:]:
        container.set_asset_decision().execute(other, "rejected")
    adopted = dashboard.get(project.id)
    assert adopted["workflow"]["shots"] == {"done": 1, "total": 1}
    assert adopted["workflow"]["primary_next"]["kind"] == "create_csp_handoff"
    assert adopted["workflow"]["release"]["done"] is None

    handoff = container.csp_handoff().build(
        project.id,
        [
            PagePlan(
                page_no=1,
                panels=[
                    PanelSlot(
                        panel_no=1,
                        shot_id=str(shot.id),
                        script_event_ids=[],
                        asset_id=aid,
                    )
                ],
            )
        ],
        script_rows=[],
    )
    assert handoff.revision
    ready = dashboard.get(project.id)
    assert ready["workflow"]["primary_next"]["kind"] == "prepare_release"
    assert ready["workflow"]["csp"]["done"] is True
    assert ready["workflow"]["release"] == {"ready": True, "done": None}
