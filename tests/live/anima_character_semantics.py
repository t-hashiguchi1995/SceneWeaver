"""Character Semantic Specs for Anima tag path + Gate 2.6.

Shared semantic → Anima compiler (tags) / MOSS compiler (caption).
Standard fixtures stay general (safe). Adult tokens are NOT included here.

Identity tags prefer ANIMADEX Trigger + character tags, cross-checked with
official visuals. See docs/validation/animadex-character-evaluation.md.
"""

from __future__ import annotations

from typing import Any, TypedDict


class CharacterSemantic(TypedDict):
    fixture_id: str
    display_name: str
    character_name: str  # tag form (ANIMADEX trigger character half)
    franchise: str  # ANIMADEX trigger franchise half
    subject_tags: list[str]
    identity_tags: list[str]  # appearance only (no subject / name / franchise)
    outfit_tags: str
    expression: str
    pose: str
    camera_shot: str
    camera_angle: str
    background: str
    lighting: str
    content_rating: str
    animadex_url: str


# Gate 2.6 Primary refine targets (Anima Base → edit → regenerate → adopt)
GATE26_PRIMARY: list[CharacterSemantic] = [
    {
        "fixture_id": "C01",
        "display_name": "リゼ・ヘルエスタ",
        "character_name": "lize helesta",
        "franchise": "nijisanji",
        "subject_tags": ["1girl"],
        "identity_tags": [
            "purple eyes",
            "white hair",
            "blue hair",
            "two-tone hair",
            "colored inner hair",
            "long hair",
            "blunt bangs",
            "crown",
        ],
        "outfit_tags": "royal blue and white outfit",
        "expression": "calm expression",
        "pose": "standing",
        "camera_shot": "medium full shot",
        "camera_angle": "eye level",
        "background": "simple studio background",
        "lighting": "soft lighting",
        "content_rating": "general",
        "animadex_url": "https://animadex.net/c/lize_helesta",
    },
    {
        "fixture_id": "C04",
        "display_name": "星川サラ",
        "character_name": "hoshikawa sara",
        "franchise": "nijisanji",
        "subject_tags": ["1girl"],
        "identity_tags": [
            "heterochromia",
            "red eyes",
            "yellow eyes",
            "blonde hair",
            "long hair",
            "very long hair",
            "side ponytail",
            "x hair ornament",
            "hair ribbon",
            "ahoge",
        ],
        "outfit_tags": "idol costume, white dress, blue accents",
        "expression": "slight smile",
        "pose": "standing",
        "camera_shot": "medium full shot",
        "camera_angle": "eye level",
        "background": "simple neutral studio background",
        "lighting": "soft lighting",
        "content_rating": "general",
        "animadex_url": "https://animadex.net/c/hoshikawa_sara",
    },
    {
        "fixture_id": "C05",
        "display_name": "イレイナ",
        "character_name": "elaina (majo no tabitabi)",
        "franchise": "majo no tabitabi",
        "subject_tags": ["1girl"],
        "identity_tags": [
            "hair between eyes",
            "blue eyes",
            "long hair",
            "white hair",
            "grey hair",
            "ahoge",
            "witch hat",
            "black headwear",
        ],
        "outfit_tags": "black robe, white shirt, collared shirt, long sleeves, witch",
        "expression": "calm expression",
        "pose": "standing",
        "camera_shot": "medium full shot",
        "camera_angle": "eye level",
        "background": "simple neutral studio background",
        "lighting": "soft lighting",
        "content_rating": "general",
        "animadex_url": "https://animadex.net/c/elaina_(majo_no_tabitabi)",
    },
    {
        "fixture_id": "C08",
        "display_name": "暁美ほむら",
        "character_name": "akemi homura",
        "franchise": "mahou shoujo madoka magica",
        "subject_tags": ["1girl"],
        "identity_tags": [
            "purple eyes",
            "long hair",
            "black hair",
            "hairband",
            "hair ribbon",
        ],
        "outfit_tags": "magical girl, white jacket, black skirt, purple accents",
        "expression": "stoic expression",
        "pose": "standing",
        "camera_shot": "medium full shot",
        "camera_angle": "eye level",
        "background": "simple neutral studio background",
        "lighting": "soft lighting",
        "content_rating": "general",
        "animadex_url": "https://animadex.net/c/akemi_homura",
    },
    {
        "fixture_id": "C10",
        "display_name": "ホタル（Firefly）",
        "character_name": "firefly (honkai: star rail)",
        "franchise": "honkai (series)",
        "subject_tags": ["1girl"],
        "identity_tags": [
            "hair between eyes",
            "purple eyes",
            "grey hair",
            "long hair",
            "black hairband",
            "hair intakes",
        ],
        "outfit_tags": "white shirt, black jacket, long sleeves",
        "expression": "slight smile",
        "pose": "standing",
        "camera_shot": "medium full shot",
        "camera_angle": "eye level",
        "background": "simple neutral studio background",
        "lighting": "soft lighting",
        "content_rating": "general",
        "animadex_url": "https://animadex.net/c/firefly_(honkai:_star_rail)",
    },
]


def to_anima_render_spec(sem: CharacterSemantic) -> dict[str, Any]:
    return {
        "capability": "BaseRender",
        "content_rating": sem["content_rating"],
        "subject_tags": list(sem["subject_tags"]),
        "character_name": sem["character_name"],
        "franchise": sem["franchise"],
        "identity_tags": list(sem["identity_tags"]),
        "outfit_tags": sem["outfit_tags"],
        "expression": {"id": sem["expression"]},
        "pose": {"id": sem["pose"]},
        "camera": {"shot": sem["camera_shot"], "angle": sem["camera_angle"]},
        "background": sem["background"],
        "lighting": sem["lighting"],
    }


def to_moss_render_spec(sem: CharacterSemantic) -> dict[str, Any]:
    """Same semantic → MOSS natural-language caption path."""
    return {
        "capability": "LayoutGuidedRender",
        "content_rating": sem["content_rating"],
        "identity_tags": [
            *sem["subject_tags"],
            sem["character_name"],
            *sem["identity_tags"],
        ],
        "character_traits": f"from {sem['franchise']}" if sem["franchise"] != "original" else "",
        "outfit_tags": sem["outfit_tags"],
        "expression": {"id": sem["expression"]},
        "pose": {"id": sem["pose"]},
        "camera": {"shot": sem["camera_shot"], "angle": sem["camera_angle"]},
        "background": sem["background"],
        "lighting": sem["lighting"],
    }
