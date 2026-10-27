"""Gate 3 — Outfit isolation fixture definitions (frozen).

Primary: C01 / C06 / C07 / C10.
Each character has Outfit A/B/C with exclusive marker terms for prompt-leak checks.
"""

from __future__ import annotations

from typing import Any, TypedDict

from tests.live.moss_sft_gate2_5_fixtures import PRIMARY as G25_PRIMARY, COMMON_RENDER


class OutfitDef(TypedDict):
    key: str  # A | B | C
    title: str
    garment_description: str
    exclusive_terms: list[str]  # must appear in this outfit's prompt; forbidden on others


class CharGate3(TypedDict):
    fixture_id: str
    fixture_name: str
    slug: str
    seed: int  # same seed for A1/B/C/A2
    identity_tags: list[str]
    character_traits: str
    outfits: dict[str, OutfitDef]  # A/B/C


def _g25(fixture_id: str) -> dict[str, Any]:
    for fx in G25_PRIMARY:
        if fx["fixture_id"] == fixture_id:
            return fx
    raise KeyError(fixture_id)


def _char(
    fixture_id: str,
    seed: int,
    outfits: dict[str, OutfitDef],
) -> CharGate3:
    base = _g25(fixture_id)
    return {
        "fixture_id": fixture_id,
        "fixture_name": base["fixture_name"],
        "slug": base["slug"],
        "seed": seed,
        "identity_tags": list(base["identity_tags"]),
        "character_traits": base["character_traits"],
        "outfits": outfits,
    }


PRIMARY: list[CharGate3] = [
    _char(
        "C01",
        30101,
        {
            "A": {
                "key": "A",
                "title": "C01-A royal blue-white",
                "garment_description": (
                    "canonical blue and white royal-style frilly dress with white blouse accents, "
                    "ribbons, stockings, small crown tiara, elegant ceremony gown silhouette, "
                    "marker_royal_bluewhite_gown"
                ),
                "exclusive_terms": [
                    "royal-style",
                    "blue and white",
                    "marker_royal_bluewhite_gown",
                ],
            },
            "B": {
                "key": "B",
                "title": "C01-B casual hoodie",
                "garment_description": (
                    "casual black hoodie and blue denim skirt, sneakers, streetwear look, "
                    "no dress no gown, marker_black_hoodie_denim"
                ),
                "exclusive_terms": [
                    "black hoodie",
                    "denim skirt",
                    "marker_black_hoodie_denim",
                ],
            },
            "C": {
                "key": "C",
                "title": "C01-C red evening",
                "garment_description": (
                    "elegant floor-length red evening dress, formal gown, bare shoulders optional, "
                    "no hoodie no denim, marker_red_evening_gown"
                ),
                "exclusive_terms": [
                    "red evening dress",
                    "floor-length",
                    "marker_red_evening_gown",
                ],
            },
        },
    ),
    _char(
        "C06",
        30106,
        {
            "A": {
                "key": "A",
                "title": "C06-A idol stage",
                "garment_description": (
                    "canonical colorful pink-forward idol stage costume with frills and ribbon accents, "
                    "performance dress, marker_pink_idol_stage"
                ),
                "exclusive_terms": [
                    "idol stage costume",
                    "pink-forward",
                    "marker_pink_idol_stage",
                ],
            },
            "B": {
                "key": "B",
                "title": "C06-B oversized sweat",
                "garment_description": (
                    "casual oversized gray sweatshirt and shorts, relaxed lounge streetwear, "
                    "no stage costume, marker_oversized_sweat_shorts"
                ),
                "exclusive_terms": [
                    "oversized gray sweatshirt",
                    "shorts",
                    "marker_oversized_sweat_shorts",
                ],
            },
            "C": {
                "key": "C",
                "title": "C06-C business suit",
                "garment_description": (
                    "formal dark navy business suit with blazer and pencil skirt, office attire, "
                    "no sweatshirt no idol dress, marker_dark_business_suit"
                ),
                "exclusive_terms": [
                    "business suit",
                    "blazer",
                    "marker_dark_business_suit",
                ],
            },
        },
    ),
    _char(
        "C07",
        30107,
        {
            "A": {
                "key": "A",
                "title": "C07-A sporty idol",
                "garment_description": (
                    "canonical sporty idol stage outfit with warm orange accent colors, "
                    "active shorts or short skirt, marker_sporty_warm_idol"
                ),
                "exclusive_terms": [
                    "sporty idol",
                    "warm orange",
                    "marker_sporty_warm_idol",
                ],
            },
            "B": {
                "key": "B",
                "title": "C07-B sailor uniform",
                "garment_description": (
                    "classic navy and white school sailor uniform with pleated skirt and scarf, "
                    "no sporty stage wear, marker_navy_sailor_uniform"
                ),
                "exclusive_terms": [
                    "sailor uniform",
                    "navy and white",
                    "marker_navy_sailor_uniform",
                ],
            },
            "C": {
                "key": "C",
                "title": "C07-C winter coat",
                "garment_description": (
                    "heavy winter coat with scarf and boots, cold-weather outerwear, "
                    "no sailor uniform no stage outfit, marker_winter_coat_scarf_boots"
                ),
                "exclusive_terms": [
                    "winter coat",
                    "scarf and boots",
                    "marker_winter_coat_scarf_boots",
                ],
            },
        },
    ),
    _char(
        "C10",
        30110,
        {
            "A": {
                "key": "A",
                "title": "C10-A SF tech suit",
                "garment_description": (
                    "canonical sleek futuristic tech bodysuit with soft neon cyan trim, "
                    "sci-fi tactical silhouette, marker_sf_neon_bodysuit"
                ),
                "exclusive_terms": [
                    "futuristic tech bodysuit",
                    "neon cyan",
                    "marker_sf_neon_bodysuit",
                ],
            },
            "B": {
                "key": "B",
                "title": "C10-B pastel pajamas",
                "garment_description": (
                    "soft pastel pink pajama set, loose sleepwear top and pants, cozy indoor, "
                    "no tech suit no neon, marker_pastel_pajama_set"
                ),
                "exclusive_terms": [
                    "pastel pink pajama",
                    "sleepwear",
                    "marker_pastel_pajama_set",
                ],
            },
            "C": {
                "key": "C",
                "title": "C10-C tuxedo",
                "garment_description": (
                    "formal black tuxedo jacket and trousers with white dress shirt and bow tie, "
                    "no pajamas no bodysuit, marker_black_tuxedo_formal"
                ),
                "exclusive_terms": [
                    "black tuxedo",
                    "bow tie",
                    "marker_black_tuxedo_formal",
                ],
            },
        },
    ),
]

TURNS = ("A1", "B", "C", "A2")


def turn_outfit_key(turn: str) -> str:
    if turn in ("A1", "A2"):
        return "A"
    if turn in ("B", "C"):
        return turn
    raise ValueError(turn)


def image_name(turn: str) -> str:
    return {"A1": "A1.png", "B": "B.png", "C": "C.png", "A2": "A2_return.png"}[turn]


def framing_patch() -> dict[str, Any]:
    return {
        **COMMON_RENDER,
        "capability": "LayoutGuidedRender",
    }
