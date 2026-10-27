"""Gate 2.5 Primary fixture definitions (frozen design).

Maps each fixture to render_spec fields for moss_caption_v1.
Name alone is never enough — appearance + default outfit are always present.
"""

from __future__ import annotations

from typing import Any, TypedDict


class FixtureDef(TypedDict):
    fixture_id: str
    fixture_name: str
    slug: str
    seed: int
    tier: str  # primary | secondary
    identity_tags: list[str]
    character_traits: str
    outfit_tags: str
    identity_summary: str


# Shared render framing for all fixtures (Gate 2.5 §2).
COMMON_RENDER: dict[str, Any] = {
    "capability": "LayoutGuidedRender",
    "expression": {"id": "slight smile"},
    "pose": {"id": "standing"},
    "camera": {"shot": "medium-full", "angle": "eye_level"},
    "background": "plain studio backdrop, low-complexity neutral background",
    "content_rating": "general",
}

PRIMARY: list[FixtureDef] = [
    {
        "fixture_id": "C01",
        "fixture_name": "リゼ・ヘルエスタ",
        "slug": "lize",
        "seed": 20101,
        "tier": "primary",
        "identity_tags": [
            "1girl",
            "Lize Helesta",
            "long light-blue icy aqua hair",
            "soft waves",
            "side locks",
            "clear blue eyes",
            "small crown tiara",
        ],
        "character_traits": (
            "elegant cool-cute royalty VTuber idol impression, noble young lady"
        ),
        "outfit_tags": (
            "frilly black-and-blue gothic-lolita-inspired dress with white blouse accents, "
            "ribbons, stockings, crown accessory on head"
        ),
        "identity_summary": "Lize Helesta — light-blue long hair, blue eyes, crown, gothic-lolita dress",
    },
    {
        "fixture_id": "C02",
        "fixture_name": "栞葉るり",
        "slug": "ruri",
        "seed": 20102,
        "tier": "primary",
        "identity_tags": [
            "1girl",
            "Shioriha Ruri",
            "long soft lavender light purple hair",
            "gentle soft waves",
            "calm violet purple eyes",
            "modest hair ribbon",
        ],
        "character_traits": "quiet scholarly beauty, reserved gentle impression",
        "outfit_tags": (
            "neat white blouse with soft pastel cardigan, long muted skirt, "
            "low-contrast pastel palette"
        ),
        "identity_summary": "Shioriha Ruri — lavender long hair, violet eyes, pastel cardigan look",
    },
    {
        "fixture_id": "C03",
        "fixture_name": "夜見れな",
        "slug": "rena",
        "seed": 20103,
        "tier": "primary",
        "identity_tags": [
            "1girl",
            "Yorumi Rena",
            "long black deep purple-black hair",
            "distinctive fringe bangs",
            "sharp crimson red eyes",
            "dark choker",
        ],
        "character_traits": "dark-cute high-contrast night idol, slightly mischievous gothic vibe",
        "outfit_tags": (
            "black gothic dress with red accents, lace details, choker or dark ribbon at neck"
        ),
        "identity_summary": "Yorumi Rena — dark hair, crimson eyes, black gothic dress with red",
    },
    {
        "fixture_id": "C04",
        "fixture_name": "星川サラ",
        "slug": "sara",
        "seed": 20104,
        "tier": "primary",
        "identity_tags": [
            "1girl",
            "Hoshikawa Sara",
            "long bright blonde golden hair",
            "lively volume",
            "bright aqua blue eyes",
            "cute idol hair accessory",
        ],
        "character_traits": "cheerful sunny pop idol, high-energy impression",
        "outfit_tags": (
            "bright idol-style costume white and pastel with blue or gold accents, "
            "cute stage accessories"
        ),
        "identity_summary": "Hoshikawa Sara — blonde long hair, aqua eyes, bright idol costume",
    },
    {
        "fixture_id": "C05",
        "fixture_name": "イレイナ",
        "slug": "elaina",
        "seed": 20105,
        "tier": "primary",
        "identity_tags": [
            "1girl",
            "Elaina",
            "long ash-blonde silver-blonde hair",
            "calm blue-gray eyes",
            "wide-brim pointed witch hat",
        ],
        "character_traits": "composed wandering witch, slightly aloof traveler impression",
        "outfit_tags": (
            "dark witch robe travel cloak over blouse, pointed wide-brim witch hat, "
            "soft travel mage silhouette, satchel optional"
        ),
        "identity_summary": "Elaina — ash-blonde hair, blue-gray eyes, witch hat and cloak",
    },
    {
        "fixture_id": "C06",
        "fixture_name": "春日未来",
        "slug": "mirai",
        "seed": 20106,
        "tier": "primary",
        "identity_tags": [
            "1girl",
            "Kasuga Mirai",
            "long pink hair",
            "twin tails or half-up idol styling",
            "bright magenta pink eyes",
            "large hair ribbons",
        ],
        "character_traits": "bright earnest classic idol smile energy, youthful",
        "outfit_tags": (
            "colorful pink-forward idol stage costume with frills and ribbon accents"
        ),
        "identity_summary": "Kasuga Mirai — pink twin-tails, magenta eyes, pink idol costume",
    },
    {
        "fixture_id": "C07",
        "fixture_name": "伊吹翼",
        "slug": "tsubasa",
        "seed": 20107,
        "tier": "primary",
        "identity_tags": [
            "1girl",
            "Ibuki Tsubasa",
            "short-to-medium blonde light hair",
            "lively tomboyish volume",
            "warm amber orange eyes",
            "sporty hairband",
        ],
        "character_traits": "energetic confident athletic idol, dynamic tomboyish energy",
        "outfit_tags": (
            "sporty idol stage outfit with warm accent colors, shorts or active skirt"
        ),
        "identity_summary": "Ibuki Tsubasa — short blonde hair, amber eyes, sporty idol outfit",
    },
    {
        "fixture_id": "C08",
        "fixture_name": "暁美ほむら",
        "slug": "homura",
        "seed": 20108,
        "tier": "primary",
        "identity_tags": [
            "1girl",
            "Akemi Homura",
            "long straight black hair",
            "deep purple eyes",
            "hair ribbon bow",
        ],
        "character_traits": "stoic dark magical-girl, serious restrained cool impression",
        "outfit_tags": (
            "dark magical-girl uniform black and deep purple with white shirt accents, "
            "skirt, ribbon"
        ),
        "identity_summary": "Akemi Homura — long black hair, purple eyes, dark magical-girl uniform",
    },
    {
        "fixture_id": "C09",
        "fixture_name": "鹿目まどか",
        "slug": "madoka",
        "seed": 20109,
        "tier": "primary",
        "identity_tags": [
            "1girl",
            "Kaname Madoka",
            "pink hair in twin tails",
            "pink rose eyes",
            "soft hair ribbons",
        ],
        "character_traits": "warm hopeful kind magical-girl, gentle contrast to Homura",
        "outfit_tags": (
            "pink-and-white magical-girl outfit with ribbons, short skirt, soft frills"
        ),
        "identity_summary": "Kaname Madoka — pink twin tails, rose eyes, pink-white magical-girl outfit",
    },
    {
        "fixture_id": "C10",
        "fixture_name": "ホタル",
        "slug": "hotaru",
        "seed": 20110,
        "tier": "primary",
        "identity_tags": [
            "1girl",
            "Hotaru",
            "original android SF girl named Hotaru",
            "short-to-medium silver pale blue hair",
            "clean cool cut",
            "luminous cyan tech-glow eyes",
        ],
        "character_traits": (
            "cool synthetic-beauty sci-fi impression, subtle HUD tech accents, clean SF silhouette"
        ),
        "outfit_tags": (
            "sleek futuristic bodysuit or tech jacket and pants, minimal logos, soft neon trim"
        ),
        "identity_summary": "Hotaru (original SF) — silver/pale-blue hair, cyan eyes, tech outfit",
    },
    {
        "fixture_id": "C11",
        "fixture_name": "実写系の成人女性コスプレイヤー（オリジナル）",
        "slug": "liveaction_adult",
        "seed": 20111,
        "tier": "primary",
        "identity_tags": [
            "photorealistic photo of an adult Japanese woman",
            "mid-20s adult cosplayer",
            "original fictional person",
            "shoulder-length dark brown hair",
            "natural soft waves",
            "dark brown eyes",
            "live-action photography look",
            "not anime",
            "not illustration",
        ],
        "character_traits": (
            "approachable adult cosplayer between shoots, soft studio beauty lighting, "
            "photoreal live-action, no real celebrity likeness"
        ),
        "outfit_tags": (
            "simple modern casual white blouse and dark skirt, convention-badge-free, "
            "no real-brand logos"
        ),
        "identity_summary": (
            "Original adult photoreal cosplayer — dark brown hair/eyes, casual blouse, live-action"
        ),
    },
]


def render_patch(fx: FixtureDef) -> dict[str, Any]:
    return {
        **COMMON_RENDER,
        "identity_tags": list(fx["identity_tags"]),
        "character_traits": fx["character_traits"],
        "outfit_tags": fx["outfit_tags"],
    }


def image_basename(fx: FixtureDef) -> str:
    return f"{fx['fixture_id']}_{fx['slug']}.png"
