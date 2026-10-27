"""Anima tag-sequence compiler helpers (Danbooru-style ordered slots).

Order (Production Fair vs MOSS natural-language captions):

  quality → rating → subject → character → franchise → artist_style →
  identity → body → outfit → expression → pose → camera → background → lighting

Adult rating tokens belong only on the adult rating profile — never on standard
character fixtures (general).
"""

from __future__ import annotations

from typing import Any

# Fixed quality stack for Stock Anima / Illustrious-class models.
ANIMA_QUALITY_TAGS = (
    "year 2025",
    "newest",
    "masterpiece",
    "best quality",
    "score_9",
    "score_8",
    "highres",
)

# General (safe-for-work) rating. Standard character fixtures use this.
ANIMA_RATING_GENERAL = ("safe",)

# Adult rating profile — only when content_rating == "adult" AND adult fixture.
# Not used for Gate 2.5 / Gate 2.6 standard characters.
ANIMA_RATING_ADULT = ("sensitive",)

ANIMA_ARTIST_DEFAULT = ("@fuzichoco", "@rella")

ANIMA_NEGATIVE = (
    "worst quality, low quality, score_1, score_2, score_3, blurry, jpeg artifacts, "
    "sepia, bad anatomy, bad hands, text, error, missing fingers, extra digit, "
    "fewer digits, cropped, signature, watermark, username, artist name"
)

_SUBJECT_TOKENS = frozenset(
    {
        "1girl",
        "1boy",
        "1other",
        "2girls",
        "2boys",
        "3girls",
        "multiple girls",
        "multiple boys",
    }
)


def _as_tokens(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        out: list[str] = []
        for item in value:
            out.extend(_as_tokens(item))
        return out
    text = str(value).strip()
    if not text:
        return []
    return [part.strip() for part in text.split(",") if part.strip()]


def _dedupe(tokens: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for tok in tokens:
        key = tok.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(tok)
    return out


def _spec_id(value: Any, default: str) -> str:
    if isinstance(value, dict):
        return str(value.get("id") or default)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return default


def _camera_tokens(render_spec: dict[str, Any]) -> list[str]:
    raw = render_spec.get("camera")
    camera = raw if isinstance(raw, dict) else {}
    shot = str(camera.get("shot") or "medium full shot").replace("_", " ").strip()
    angle = str(camera.get("angle") or "eye level").replace("_", " ").strip()
    # Normalize common underscored ids
    if shot == "medium":
        shot = "medium shot"
    if shot == "medium-full":
        shot = "medium full shot"
    if angle == "eye_level":
        angle = "eye level"
    return [shot, angle]


def split_subject_and_identity(identity_tags: list[str]) -> tuple[list[str], list[str]]:
    """Pull subject-count tags out of identity_tags when subject_tags omitted."""
    subject: list[str] = []
    appearance: list[str] = []
    for tok in identity_tags:
        if tok.lower() in _SUBJECT_TOKENS:
            subject.append(tok)
        else:
            appearance.append(tok)
    return subject, appearance


def rating_tags_for(content_rating: str, *, rating_profile: str | None = None) -> list[str]:
    """Return rating slot tags.

    ``rating_profile`` overrides: ``general`` | ``adult``.
    Default: general → safe; adult → sensitive (never auto-inject nsfw/explicit
    for standard fixtures — adult fixtures opt in via content_rating/adult profile).
    """
    profile = (rating_profile or content_rating or "general").lower()
    if profile == "adult":
        return list(ANIMA_RATING_ADULT)
    return list(ANIMA_RATING_GENERAL)


def compile_anima_positive(render_spec: dict[str, Any]) -> str:
    """Assemble ordered Anima tag sequence from Character Semantic Spec fields."""
    content_rating = str(render_spec.get("content_rating") or "general")
    rating_profile = render_spec.get("rating_profile")
    rating = rating_tags_for(content_rating, rating_profile=str(rating_profile) if rating_profile else None)

    subject = _as_tokens(render_spec.get("subject_tags"))
    identity_raw = _as_tokens(render_spec.get("identity_tags") or ["1girl"])
    if not subject:
        subject, identity_appearance = split_subject_and_identity(identity_raw)
        if not subject:
            subject = ["1girl"]
    else:
        # Drop subject tokens duplicated inside identity_tags
        _, identity_appearance = split_subject_and_identity(identity_raw)

    character_name = str(render_spec.get("character_name") or "").strip()
    franchise = str(render_spec.get("franchise") or "").strip()

    # Avoid duplicating character_name inside identity appearance
    if character_name:
        identity_appearance = [
            t for t in identity_appearance if t.lower() != character_name.lower()
        ]

    artists = _as_tokens(render_spec.get("artist_style_tags"))
    if not artists:
        artists = list(ANIMA_ARTIST_DEFAULT)

    body = _as_tokens(render_spec.get("body_tags"))
    if not body and render_spec.get("body"):
        body = _as_tokens(render_spec.get("body"))

    outfit = _as_tokens(render_spec.get("outfit_tags") or "casual clothes")
    expression = [_spec_id(render_spec.get("expression"), "slight smile")]
    pose = [_spec_id(render_spec.get("pose"), "standing")]
    camera = _camera_tokens(render_spec)
    background = _as_tokens(render_spec.get("background") or "simple neutral studio background")
    lighting = _as_tokens(render_spec.get("lighting") or "soft lighting")

    slots: list[list[str]] = [
        list(ANIMA_QUALITY_TAGS),
        rating,
        subject,
        [character_name] if character_name else [],
        [franchise] if franchise else [],
        artists,
        identity_appearance,
        body,
        outfit,
        expression,
        pose,
        camera,
        background,
        lighting,
    ]
    tokens: list[str] = []
    for slot in slots:
        tokens.extend(slot)
    return ", ".join(_dedupe(tokens))
