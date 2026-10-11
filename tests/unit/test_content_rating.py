"""Content-rating checks use neutral markers, without sexual content or generation."""

import pytest

from creator_studio.application.projects.create_project import CreateProjectCommand
from creator_studio.application.prompt.assembly import build_default_prompt
from creator_studio.application.prompt.renderer import PromptRenderer
from creator_studio.domain.prompt.assembly import PromptAssemblyProfile, PromptComponent


@pytest.mark.parametrize("negative", [False, True])
def test_general_profile_excludes_adult_components_and_modifiers(negative):
    component = PromptComponent(
        "rating:adult", "user_additions", "restricted marker, <lora:restricted:0.8>",
        content_rating="adult", negative=negative,
    )
    built = build_default_prompt([component], PromptAssemblyProfile())
    assert built.positive == built.negative == ""
    assert built.components == []
    assert built.model_modifiers == []
    assert built.warnings == ["content policy excluded rating:adult@v1"]


def test_adult_assembly_profile_accepts_general_and_adult_markers():
    components = [
        PromptComponent("rating:general", "user_additions", "general marker"),
        PromptComponent("rating:adult", "user_additions", "restricted marker", content_rating="adult"),
        PromptComponent("rating:unknown", "user_additions", "unknown marker", content_rating="unknown"),
    ]
    built = build_default_prompt(components, PromptAssemblyProfile(content_rating="adult"))
    assert set(built.positive.split(", ")) == {"general marker", "restricted marker"}
    assert built.warnings == ["content policy excluded rating:unknown@v1"]


def test_renderer_currently_uses_general_profile_even_with_adult_spec():
    rendered = PromptRenderer().render_anima({
        "prompt_profile_id": "anima_story_panel",
        "content_rating": "adult",
        "prompt_components": [{
            "component_id": "rating:adult", "kind": "user_additions",
            "text": "restricted marker", "content_rating": "adult",
        }],
    })
    assert "restricted marker" not in rendered.positive
    assert "rating:adult@v1" not in rendered.assembly_metadata["component_refs"]
    assert "content policy excluded rating:adult@v1" in rendered.assembly_metadata["warnings"]


def test_adult_project_rating_round_trips(container):
    project = container.create_project().execute(
        CreateProjectCommand(title="Rating persistence test", content_rating="adult")
    )
    with container.uow() as uow:
        stored = uow.projects.get(project.id)
    assert stored.content_rating == "adult"
