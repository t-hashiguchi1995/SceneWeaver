from __future__ import annotations

from pathlib import Path

import pytest

from creator_studio.application.csp.handoff import PagePlan, PanelSlot
from creator_studio.application.projects.create_project import CreateProjectCommand
from creator_studio.application.shots.pipeline import PromptCompiler
from creator_studio.infrastructure.container import Container


def test_prompt_compiler_golden() -> None:
    compiled = PromptCompiler().compile_anima(
        {
            "identity_tags": ["1girl", "black_hair"],
            "outfit_tags": "cardigan",
            "expression": {"id": "shy"},
            "pose": {"id": "look_over_shoulder"},
            "camera": {"shot": "medium", "angle": "eye_level"},
        }
    )
    assert "masterpiece" in compiled["positive"]
    assert "black_hair" in compiled["positive"]
    assert "look_over_shoulder" in compiled["positive"]
    assert "worst quality" in compiled["negative"]


def test_shot_render_provenance_and_stale(container: Container) -> None:
    project = container.create_project().execute(CreateProjectCommand(title="Vis"))
    char = container.create_character().execute("A")
    scene = container.create_scene().execute(project.id, "S")
    beat = container.create_beat().execute(scene.id, intent="stay", speaker_id=char.id)
    pipe = container.shot_pipeline()
    shot = pipe.plan_shot(beat.id)
    rendered = pipe.render(shot.id, use_pose=True, pose_asset_uri="asset://pose/fixture.png")
    assert len(rendered["output_asset_ids"]) == 4
    assert rendered["is_current"] is True
    attempt = pipe.get_attempt(rendered["generation_attempt_id"])
    assert attempt.based_on_shot_revision == shot.revision
    assert attempt.workflow_hash
    plan = pipe.get_plan(rendered["render_plan_id"])
    assert plan.stale_reason is None

    pipe.invalidate_for_script_change(beat.id)
    with pytest.raises(ValueError, match="stale"):
        pipe.render(shot.id)
    stale_shot = pipe.get_shot(shot.id)
    assert stale_shot.stale_reason == "script_revision"
    assert pipe.get_plan(rendered["render_plan_id"]).stale_reason == "script_revision"
    # generation remains immutable historical record; currentness is derived
    reloaded = pipe.get_attempt(rendered["generation_attempt_id"])
    assert reloaded.status == "succeeded"
    assert reloaded.is_current_for(stale_shot.revision) is True
    assert reloaded.based_on_shot_revision == rendered["shot_revision"]
    assert reloaded.workflow_hash == attempt.workflow_hash
    assert reloaded.payload == attempt.payload


def test_csp_handoff_and_release_preview(container: Container) -> None:
    from creator_studio.application.assets.store_asset import StoreBytesCommand
    from creator_studio.domain.asset import AssetKind

    png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
        b"\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    a1 = container.store_asset().execute(
        StoreBytesCommand(
            data=png + b"p1",
            kind=AssetKind.GENERATED,
            mime="image/png",
            relative_dir="generated",
            filename="p1.png",
        )
    )
    a2 = container.store_asset().execute(
        StoreBytesCommand(
            data=png + b"p2",
            kind=AssetKind.GENERATED,
            mime="image/png",
            relative_dir="generated",
            filename="p2.png",
        )
    )
    container.set_asset_decision().execute(a1.id, "adopted")
    container.set_asset_decision().execute(a2.id, "adopted")
    pages = [
        PagePlan(
            page_no=1,
            panels=[
                PanelSlot(
                    panel_no=1,
                    shot_id="shot_a",
                    script_event_ids=["evt1"],
                    asset_id=a1.id,
                ),
                PanelSlot(
                    panel_no=2,
                    shot_id="shot_b",
                    script_event_ids=["evt2"],
                    asset_id=a2.id,
                ),
            ],
        )
    ]
    result = container.csp_handoff().build(
        "proj1",
        pages,
        script_rows=[
            {"id": "evt1", "kind": "speech", "speaker": "A", "text": "……もう少しだけ"},
            {"id": "evt2", "kind": "speech", "speaker": "A", "text": "一緒に。"},
        ],
    )
    root = Path(result.path)
    assert (root / "project_manifest.json").exists()
    assert (root / "script" / "script_events.tsv").exists()
    assert result.manifest["pages"][0]["panels"][0]["shot_id"] == "shot_a"
    assert result.manifest["pages"][0]["panels"][0]["asset_id"] == a1.id

    preview = container.release_preview().build_editions(
        title="Demo Release",
        summary="A short teaser",
        hashtags=["#SceneWeaver", "#demo"],
    )
    assert preview["editions"]["x"]["text"]
    assert preview["editions"]["pixiv"]["ai_disclosure"] is True
    assert "Preview only" in preview["note"]