"""Canonical character visual presets used by seed and CreateCharacter."""

from __future__ import annotations

from creator_studio.domain.character.models import VisualIdentity

# Matches tests/fixtures/story/rize_user_prompt.txt (line 1 base fragment).
LIZE_HELESTA_IDENTITY_TAGS = [
    "lize helesta",
    "nijisanji",
]

LIZE_HELESTA_BODY = "large breasts"

# Quality tokens that belong with the Anima legacy / Rize base (not "safe").
ANIMA_RIZE_QUALITY_POSITIVE = (
    "year 2025, newest, masterpiece, best quality, score_9, score_8, highres, "
    "sensitive, nsfw, explicit"
)

ANIMA_RIZE_STYLE = "@fuzichoco, @rella"


def is_lize_helesta_name(display_name: str) -> bool:
    normalized = display_name.strip().casefold()
    return any(
        token in normalized
        for token in (
            "リゼ",
            "lize",
            "helesta",
            "ヘルエスタ",
        )
    )


def lize_helesta_visual_identity(**overrides: object) -> VisualIdentity:
    """Base VisualIdentity for リゼ・ヘルエスタ prompt assembly."""
    base = VisualIdentity(
        identity_tags=list(LIZE_HELESTA_IDENTITY_TAGS),
        body=LIZE_HELESTA_BODY,
    )
    fields = {**base.__dict__, **overrides}
    return VisualIdentity(**fields)  # type: ignore[arg-type]
