from pathlib import Path

from creator_studio.application.prompt.assembly import build_default_prompt, components_from_context
from creator_studio.application.prompt.context import resolve_prompt_context
from creator_studio.application.projects.create_project import CreateProjectCommand
from creator_studio.domain.character.presets import (
    ANIMA_RIZE_QUALITY_POSITIVE,
    ANIMA_RIZE_STYLE,
    LIZE_HELESTA_BODY,
    LIZE_HELESTA_IDENTITY_TAGS,
)
from creator_studio.domain.prompt.assembly import PromptAssemblyProfile
from creator_studio.infrastructure.container import Container


def test_lize_create_character_gets_canonical_visual_base(container: Container) -> None:
    character = container.create_character().execute("リゼ・ヘルエスタ")
    assert character.visual_identity["identity_tags"] == LIZE_HELESTA_IDENTITY_TAGS
    assert character.visual_identity["body"] == LIZE_HELESTA_BODY


def test_lize_anima_legacy_assembles_rize_base_prefix(container: Container) -> None:
    fixture = (
        Path(__file__).resolve().parents[1] / "fixtures/story/rize_user_prompt.txt"
    ).read_text().splitlines()[0].rstrip(",").strip()

    character = container.create_character().execute("リゼヘル")
    project = container.create_project().execute(CreateProjectCommand(title="Lize base"))
    scene = container.create_scene().execute(project.id, "Cafe")
    beat = container.create_beat().execute(
        scene.id, intent="stay", speaker_id=character.id
    )
    shot = container.shot_pipeline().plan_shot(beat.id)
    container.shot_pipeline().update_shot(
        shot.id,
        {
            "prompt_profile_id": "anima_story_panel",
            "prompt_quality_profile_id": "anima_legacy_v1",
        },
    )
    with container.uow() as uow:
        stored = uow.shots.get(shot.id)
        assert stored is not None
        spec = resolve_prompt_context(uow, stored)

    built = build_default_prompt(components_from_context(spec), PromptAssemblyProfile())
    expected_prefix = (
        f"{ANIMA_RIZE_QUALITY_POSITIVE}, 1girl, "
        f"{', '.join(LIZE_HELESTA_IDENTITY_TAGS)}, {ANIMA_RIZE_STYLE}, {LIZE_HELESTA_BODY}"
    )
    assert built.positive.startswith(expected_prefix)
    for token in fixture.split(", "):
        assert token in built.positive


def test_anima_legacy_quality_no_longer_uses_safe() -> None:
    built = build_default_prompt(
        components_from_context({"prompt_quality_profile_id": "anima_legacy_v1"}),
        PromptAssemblyProfile(),
    )
    assert "safe" not in built.positive.split(", ")
    assert "sensitive" in built.positive
    assert "nsfw" in built.positive
    assert "explicit" in built.positive
