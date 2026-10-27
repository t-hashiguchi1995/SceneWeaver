"""Anima tag-sequence compiler — ordered slots + franchise + rating split."""

from __future__ import annotations

from creator_studio.application.prompt.anima_tags import compile_anima_positive, rating_tags_for
from creator_studio.application.prompt.renderer import PromptRenderer
from tests.live.anima_character_semantics import GATE26_PRIMARY, to_anima_render_spec, to_moss_render_spec


def test_lize_anima_tag_order_includes_franchise_and_character() -> None:
    sem = next(s for s in GATE26_PRIMARY if s["fixture_id"] == "C01")
    positive = compile_anima_positive(to_anima_render_spec(sem))
    assert positive.startswith(
        "year 2025, newest, masterpiece, best quality, score_9, score_8, highres, safe,"
    )
    assert "1girl" in positive
    assert "lize helesta" in positive
    assert "nijisanji" in positive
    assert "@fuzichoco" in positive and "@rella" in positive
    assert "purple eyes" in positive
    assert "two-tone hair" in positive
    assert "crown" in positive
    assert "royal blue and white outfit" in positive
    # Standard fixture must not inject adult sexual rating stack
    assert "nsfw" not in positive.lower()
    assert "explicit" not in positive.lower()
    assert "large breasts" not in positive.lower()
    # character_name appears before franchise in sequence
    assert positive.index("lize helesta") < positive.index("nijisanji")
    assert positive.index("nijisanji") < positive.index("@fuzichoco")


def test_homura_includes_madoka_franchise_tag() -> None:
    sem = next(s for s in GATE26_PRIMARY if s["fixture_id"] == "C08")
    positive = compile_anima_positive(to_anima_render_spec(sem))
    assert "akemi homura" in positive
    assert "mahou shoujo madoka magica" in positive


def test_adult_rating_profile_uses_sensitive_not_on_general() -> None:
    assert rating_tags_for("general") == ["safe"]
    assert rating_tags_for("adult") == ["sensitive"]
    general = compile_anima_positive(
        {"identity_tags": ["1girl"], "content_rating": "general"}
    )
    adult = compile_anima_positive(
        {"identity_tags": ["1girl"], "content_rating": "adult"}
    )
    assert "safe" in general
    assert "sensitive" in adult
    assert "safe" not in adult


def test_production_fair_moss_does_not_get_anima_artists() -> None:
    sem = next(s for s in GATE26_PRIMARY if s["fixture_id"] == "C01")
    anima = PromptRenderer().render_anima(to_anima_render_spec(sem))
    moss = PromptRenderer().render_moss(to_moss_render_spec(sem))
    assert "@fuzichoco" in anima.positive
    assert "nijisanji" in anima.positive
    assert "@fuzichoco" not in moss.positive
    assert "score_9" not in moss.positive
    assert "Illustration of" in moss.positive or "lize helesta" in moss.positive.lower()


def test_renderer_anima_path_uses_tag_compiler() -> None:
    rendered = PromptRenderer().render_anima(
        {
            "character_name": "hoshikawa sara",
            "franchise": "nijisanji",
            "identity_tags": ["1girl", "long blonde hair", "blue eyes"],
            "outfit_tags": "idol costume",
            "expression": {"id": "slight smile"},
            "pose": {"id": "standing"},
            "camera": {"shot": "medium full shot", "angle": "eye level"},
            "background": "simple studio background",
        }
    )
    assert rendered.source_ref == "anima_compiler_v1"
    assert "hoshikawa sara" in rendered.positive
    assert "nijisanji" in rendered.positive
    assert rendered.assembly_metadata.get("franchise") == "nijisanji"


def test_renderer_prefers_saved_anima_positive() -> None:
    saved = (
        "year 2025, newest, masterpiece, best quality, score_9, score_8, highres, safe, "
        "1girl, lize helesta, nijisanji, bright blue eyes, silver crown"
    )
    rendered = PromptRenderer().render_anima(
        {
            "character_name": "lize helesta",
            "franchise": "nijisanji",
            "identity_tags": ["1girl", "blue eyes"],
            "_saved_anima_positive": saved,
        }
    )
    assert rendered.positive == saved
    assert rendered.assembly_metadata.get("compiler") == "anima_saved_character_prompt"
    assert rendered.assembly_metadata.get("saved_anima_positive") is True
