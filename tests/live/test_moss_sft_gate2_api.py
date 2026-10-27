"""Gate 2 API vertical (UI-less companion): capability → moss draft → render → adopt.

Full browser UI Gate 2 is ``pnpm test:moss:gate2:e2e:live:required``.
This pytest path proves Review/Adopt data plane when Playwright navigation is flaky.
"""

from __future__ import annotations

import os

import pytest

from pathlib import Path

from creator_studio.application.projects.create_project import CreateProjectCommand
from creator_studio.domain.asset import ReviewDecision
from creator_studio.domain.prompt import MOSS_COMPILER_SOURCE_REF
from creator_studio.infrastructure.container import Container, reset_container
from creator_studio.infrastructure.db.migrate import upgrade_head
from creator_studio.infrastructure.db.session import reset_engine
from creator_studio.infrastructure.settings import Settings, clear_settings_cache

# Reuse Gate 1 env gate.
from tests.live.test_moss_sft_live import _require_moss_runtime

pytestmark = pytest.mark.skipif(
    os.environ.get("SCENEWEAVER_MOSS_LIVE", "").lower() not in {"1", "true", "yes"},
    reason="Set SCENEWEAVER_MOSS_LIVE=1 or run via pnpm test:moss:live after Gate2 API flag",
)


@pytest.fixture()
def live_container(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Container, str]:
    runtime = tmp_path / "runtime-moss-gate2"
    runtime.mkdir()
    db = runtime / "live.db"
    comfy_url = os.environ.get("SCENEWEAVER_COMFY_URL", "http://127.0.0.1:8188")
    monkeypatch.setenv("SCENEWEAVER_RUNTIME_DIR", str(runtime))
    monkeypatch.setenv("SCENEWEAVER_DATABASE_URL", f"sqlite:///{db}")
    monkeypatch.setenv("SCENEWEAVER_ENVIRONMENT", "live-test")
    monkeypatch.setenv("SCENEWEAVER_IMAGE_BACKEND", "comfy")
    monkeypatch.setenv("SCENEWEAVER_COMFY_URL", comfy_url)
    monkeypatch.setenv("SCENEWEAVER_IMAGE_TAGGER", "off")
    monkeypatch.setenv("SCENEWEAVER_COMFY_POLL_TIMEOUT_SECONDS", "1200")
    clear_settings_cache()
    reset_engine()
    reset_container()
    settings = Settings()
    upgrade_head(settings.sqlalchemy_url())
    reset_engine()
    version = _require_moss_runtime(comfy_url)
    return Container(settings), version


def test_gate2_api_moss_render_and_adopt(live_container: tuple[Container, str]) -> None:
    c, _comfy_version = live_container
    project = c.create_project().execute(CreateProjectCommand(title="MOSS Gate2 API"))
    char = c.create_character().execute("Gate2Char")
    scene = c.create_scene().execute(project.id, "Studio")
    beat = c.create_beat().execute(scene.id, intent="portrait", speaker_id=char.id)
    pipe = c.shot_pipeline()
    shot = pipe.plan_shot(beat.id)

    # UI equivalent: generation engine → LayoutGuidedRender
    pipe.update_shot(
        shot.id,
        {
            "capability": "LayoutGuidedRender",
            "identity_tags": ["1girl", "long hair"],
            "outfit_tags": "simple blouse",
            "background": "plain studio backdrop",
        },
    )
    draft = c.prompt_draft_service().ensure_for_shot(shot.id)
    assert draft.source_ref == MOSS_COMPILER_SOURCE_REF

    rendered = pipe.render(shot.id, seed=23456)
    assert rendered["output_asset_ids"]
    attempt = pipe.get_attempt(rendered["generation_attempt_id"])
    assert attempt.payload["capability"] == "LayoutGuidedRender"
    assert attempt.payload["model_id"] == "moss_image_sft"

    asset_id = rendered["output_asset_ids"][0]
    # UI equivalent: Generation Review → Adopt
    c.set_asset_decision().execute(asset_id, "adopted")
    with c.uow() as uow:
        asset = uow.assets.get(asset_id)
        assert asset is not None
        assert asset.review_decision == ReviewDecision.ADOPTED
