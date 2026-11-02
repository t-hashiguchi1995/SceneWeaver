"""Shared A3 Pose Gallery prompt builders — identity vs outfit separation.

Rules:
- Character identity must not carry outfit accessories (e.g. crown).
- Test markers belong in manifests only — never in model prompts.
- Reference-path pose cues stay side-agnostic (no left/right) so flip can own laterality.
"""

from __future__ import annotations

_FRAME = "full body, entire body visible, from head to toe, wide shot, feet visible"

_OUTFIT_A = "royal blue and white dress, blue jacket, white blouse, silver crown"
_OUTFIT_B = "red cardigan, white blouse, plaid skirt, loafers, school uniform"

# Manifest-only marker — must never appear in final_positive_prompt.
OUTFIT_B_MANIFEST_MARKER = "a3_outfit_b_marker"

_CROWN_TOKENS = frozenset({"crown", "silver crown"})


def strip_crown_tokens(text: str) -> str:
    parts = [
        p.strip()
        for p in text.split(",")
        if p.strip() and p.strip().lower() not in _CROWN_TOKENS
    ]
    return ", ".join(parts)


def identity_core_from_adopted(adopted: str) -> str:
    """Keep identity through feather ornament; drop dress and crown."""
    marker = ", royal blue and white dress"
    core = adopted.split(marker)[0] if marker in adopted else adopted
    return strip_crown_tokens(core)


def assert_no_test_markers(prompt: str) -> None:
    lowered = prompt.lower()
    assert OUTFIT_B_MANIFEST_MARKER not in prompt
    assert "a3_outfit" not in lowered


def prompt_p01_hand_on_head(adopted: str) -> str:
    core = identity_core_from_adopted(adopted)
    return (
        f"{core}, {_OUTFIT_A}, calm expression, "
        f"sitting on ground, one knee raised, "
        f"one hand on top of head, palm flat on scalp, arm raised above head, "
        f"other forearm resting on raised knee, opposite leg extended, "
        f"asymmetric pose, {_FRAME}, eye level, simple studio background, soft lighting"
    )


def prompt_ref_locked(adopted: str, outfit: str) -> str:
    """Shared locked pose for P02/P03/P05. Outfit string owns crown if needed."""
    core = identity_core_from_adopted(adopted)
    # Safety: never let crown leak from outfit B callers that forget.
    if "cardigan" in outfit.lower() or "plaid" in outfit.lower():
        outfit = strip_crown_tokens(outfit)
    text = (
        f"{core}, {outfit}, calm expression, "
        f"sitting on ground, one knee raised toward chest, "
        f"one hand on top of head, palm flat on scalp, arm raised above head, "
        f"other forearm resting on raised knee, opposite leg extended along ground, "
        f"asymmetric seated pose, pose follows reference, {_FRAME}, "
        f"eye level, simple studio background, soft lighting"
    )
    assert_no_test_markers(text)
    assert "left" not in text.lower()
    assert "right" not in text.lower()
    return text


OUTFIT_A = _OUTFIT_A
OUTFIT_B = _OUTFIT_B
FRAME = _FRAME
