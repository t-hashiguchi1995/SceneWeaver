"""Gate 2.6 — human-refined Anima tag prompts (Base → Edited).

Edited prompts keep ANIMADEX Trigger + strengthen GT checklist items
(hair / eyes / hairstyle / accessory / default outfit).
See docs/validation/anima-gate2_6/ground_truth.md.
"""

from __future__ import annotations

from typing import TypedDict


class Gate26Edit(TypedDict):
    fixture_id: str
    seed: int
    slug: str
    edit_notes: str
    edited_positive: str


GATE26_SEEDS: dict[str, int] = {
    "C01": 26001,
    "C04": 26004,
    "C05": 26005,
    "C08": 26008,
    "C10": 26010,
}

_QUALITY = (
    "year 2025, newest, masterpiece, best quality, score_9, score_8, highres, safe"
)

EDITS: dict[str, Gate26Edit] = {
    "C01": {
        "fixture_id": "C01",
        "seed": 26001,
        "slug": "lize",
        "edit_notes": (
            "ANIMADEX: purple eyes + two-tone white/blue + blunt bangs; "
            "official crown; royal blue/white"
        ),
        "edited_positive": (
            f"{_QUALITY}, 1girl, lize helesta, lize helesta, nijisanji, "
            "@fuzichoco, @rella, "
            "purple eyes, detailed eyes, "
            "white hair, blue hair, two-tone hair, colored inner hair, long hair, blunt bangs, "
            "crown, silver crown, feather hair ornament, "
            "royal blue and white dress, blue jacket, white blouse, "
            "calm expression, standing, medium full shot, eye level, "
            "simple studio background, soft lighting"
        ),
    },
    "C04": {
        "fixture_id": "C04",
        "seed": 26004,
        "slug": "sara",
        "edit_notes": (
            "ANIMADEX: heterochromia red/yellow; side ponytail; x hair ornament; "
            "idol white/blue"
        ),
        "edited_positive": (
            f"{_QUALITY}, 1girl, hoshikawa sara, hoshikawa sara, nijisanji, "
            "@fuzichoco, @rella, "
            "heterochromia, red eyes, yellow eyes, detailed eyes, "
            "blonde hair, long hair, very long hair, side ponytail, ahoge, "
            "x hair ornament, hair ribbon, "
            "idol costume, white dress, blue accents, frills, "
            "slight smile, standing, medium full shot, eye level, "
            "simple neutral studio background, soft lighting"
        ),
    },
    "C05": {
        "fixture_id": "C05",
        "seed": 26005,
        "slug": "elaina",
        "edit_notes": (
            "ANIMADEX: white/grey long hair + witch hat + black robe + white shirt; "
            "hair between eyes"
        ),
        "edited_positive": (
            f"{_QUALITY}, 1girl, elaina (majo no tabitabi), elaina (majo no tabitabi), "
            "majo no tabitabi, "
            "@fuzichoco, @rella, "
            "hair between eyes, blue eyes, detailed eyes, "
            "long hair, white hair, grey hair, ahoge, "
            "witch hat, black headwear, "
            "black robe, white shirt, collared shirt, long sleeves, witch, "
            "calm expression, standing, medium full shot, eye level, "
            "simple neutral studio background, soft lighting"
        ),
    },
    "C08": {
        "fixture_id": "C08",
        "seed": 26008,
        "slug": "homura",
        "edit_notes": (
            "ANIMADEX magical girl + official: purple eyes, black hair, hairband/ribbon, "
            "white jacket MG silhouette (avoid dark-dress drift)"
        ),
        "edited_positive": (
            f"{_QUALITY}, 1girl, akemi homura, akemi homura, "
            "mahou shoujo madoka magica, "
            "@fuzichoco, @rella, "
            "purple eyes, detailed eyes, "
            "long hair, black hair, straight hair, "
            "hairband, hair ribbon, red ribbon, "
            "magical girl, white jacket, black skirt, purple bow, soul gem, "
            "stoic expression, standing, medium full shot, eye level, "
            "simple neutral studio background, soft lighting"
        ),
    },
    "C10": {
        "fixture_id": "C10",
        "seed": 26010,
        "slug": "firefly",
        "edit_notes": (
            "ANIMADEX Firefly: grey long hair, purple eyes, black hairband, "
            "hair intakes, white shirt, black jacket — NOT tech bodysuit"
        ),
        "edited_positive": (
            f"{_QUALITY}, 1girl, firefly (honkai: star rail), firefly (honkai: star rail), "
            "honkai (series), "
            "@fuzichoco, @rella, "
            "hair between eyes, purple eyes, detailed eyes, "
            "grey hair, long hair, hair intakes, "
            "black hairband, "
            "white shirt, black jacket, long sleeves, "
            "slight smile, standing, medium full shot, eye level, "
            "simple neutral studio background, soft lighting"
        ),
    },
}


def edit_for(fixture_id: str) -> Gate26Edit:
    return EDITS[fixture_id]
