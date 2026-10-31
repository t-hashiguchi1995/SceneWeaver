"""Gate 2.7 remediation prompts (fixed seeds unchanged).

Human FAIL targets: C02 / C06 / C11 (P0), C04 secondary.
"""

from __future__ import annotations

from typing import TypedDict


class Remediation(TypedDict):
    fixture_id: str
    seed: int
    slug: str
    notes: str
    positive: str
    negative_extra: str


_QUALITY = (
    "year 2025, newest, masterpiece, best quality, score_9, score_8, highres, safe"
)

# Keep Gate 2.7 seeds identical for rematch comparability.
REMEDIATIONS: dict[str, Remediation] = {
    "C02": {
        "fixture_id": "C02",
        "seed": 27002,
        "slug": "ruri",
        "notes": (
            "Official 1st costume: silver/sandy hair, green eyes, white police hat "
            "with blue flower, white capelet, blue high-waist shorts + pantyhose, "
            "canine dog-girl silhouette (NOT lavender cardigan)."
        ),
        "positive": (
            f"{_QUALITY}, 1girl, shioriha ruri, shioriha ruri, nijisanji, "
            "@fuzichoco, @rella, "
            "dog girl, animal ears, dog ears, dog tail, "
            "green eyes, detailed eyes, "
            "silver hair, grey hair, long hair, sandy blonde-grey hair, soft waves, "
            "police hat, white hat, blue flower, flower on hat, "
            "white capelet, white shirt, id card, "
            "blue high-waist shorts, blue pantyhose, blue belt, "
            "white gloves, half gloves, blue shoes, "
            "police uniform, megaphone, "
            "calm expression, standing, medium full shot, eye level, "
            "simple studio background, soft lighting"
        ),
        "negative_extra": "school uniform, cardigan, pastel sweater, purple eyes, lavender hair",
    },
    "C04": {
        "fixture_id": "C04",
        "seed": 27004,
        "slug": "sara",
        "notes": (
            "Strengthen heterochromia (left red / right yellow) and keep "
            "side ponytail + x ornament; reinforce red/black + white/blue idol cues."
        ),
        "positive": (
            f"{_QUALITY}, 1girl, hoshikawa sara, hoshikawa sara, nijisanji, "
            "@fuzichoco, @rella, "
            "heterochromia, mismatched pupils, left eye red, right eye yellow, "
            "red eyes, yellow eyes, detailed eyes, "
            "blonde hair, long hair, very long hair, side ponytail, ahoge, "
            "x hair ornament, hair ribbon, "
            "idol costume, white dress, blue accents, red accents, black accents, frills, "
            "slight smile, standing, medium full shot, eye level, "
            "simple neutral studio background, soft lighting"
        ),
        "negative_extra": "same-colored eyes, blue eyes only, brown eyes",
    },
    "C06": {
        "fixture_id": "C06",
        "seed": 27006,
        "slug": "mirai",
        "notes": (
            "Mirai-specific: pink hair with hair clips collection cue, "
            "signature star/ribbon hair ornament, pink idol school-uniform-inspired "
            "stage costume (avoid generic pink frills)."
        ),
        "positive": (
            f"{_QUALITY}, 1girl, kasuga mirai, kasuga mirai, idolmaster, "
            "idolmaster million live, @fuzichoco, @rella, "
            "pink eyes, magenta eyes, detailed eyes, "
            "pink hair, long hair, side ponytail, hair over one shoulder, "
            "hair ornament, star hair ornament, hairclip, multiple hair clips, pink ribbon, "
            "idol costume, pink and white stage costume, sailor collar, "
            "large pink ribbon, shorts, frills, "
            "bright smile, standing, medium full shot, eye level, "
            "simple studio background, soft lighting"
        ),
        "negative_extra": "twintails, generic idol dress, purple hair, red hair",
    },
    "C11": {
        "fixture_id": "C11",
        "seed": 27011,
        "slug": "liveaction_adult",
        "notes": (
            "Strip Anima artist tags; push photoreal / raw photo tokens. "
            "Anima Base is anime-biased — rematch may still fail; policy may "
            "exclude C11 from Anima identity PASS if style remains illustrated."
        ),
        "positive": (
            "raw photo, photorealistic, realistic photograph, DSLR photo, "
            "35mm, natural skin texture, pores, soft studio beauty lighting, "
            "1girl, adult japanese woman, mid-20s, original fictional person, "
            "dark brown eyes, dark brown hair, shoulder-length hair, soft waves, "
            "white blouse, dark skirt, casual modern clothes, soft smile, "
            "standing, medium full shot, eye level, simple studio background, "
            "real person look, live-action"
        ),
        "negative_extra": (
            "anime, illustration, cartoon, drawn, cel shading, manga, "
            "2d, painterly, score_9, masterpiece, @fuzichoco, @rella, "
            "anime coloring, flat color"
        ),
    },
}
