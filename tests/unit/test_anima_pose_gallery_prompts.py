from tests.live.anima_pose_gallery_prompts import (
    OUTFIT_A,
    OUTFIT_B,
    OUTFIT_B_MANIFEST_MARKER,
    assert_no_test_markers,
    identity_core_from_adopted,
    prompt_p01_hand_on_head,
    prompt_ref_locked,
)


_ADOPTED = (
    "year 2025, newest, masterpiece, best quality, score_9, score_8, highres, safe, "
    "1girl, lize helesta, lize helesta, nijisanji, @fuzichoco, @rella, purple eyes, "
    "detailed eyes, white hair, blue hair, two-tone hair, colored inner hair, long hair, "
    "blunt bangs, crown, silver crown, feather hair ornament, royal blue and white dress, "
    "blue jacket, white blouse, calm expression, standing, medium full shot, eye level, "
    "simple studio background, soft lighting"
)


def test_identity_core_strips_crown_and_outfit() -> None:
    core = identity_core_from_adopted(_ADOPTED)
    assert "feather hair ornament" in core
    assert "crown" not in core.lower()
    assert "royal blue" not in core


def test_outfit_a_keeps_crown_outfit_b_does_not() -> None:
    a = prompt_ref_locked(_ADOPTED, OUTFIT_A)
    b = prompt_ref_locked(_ADOPTED, OUTFIT_B)
    assert "silver crown" in a
    assert "silver crown" not in b
    assert ", crown," not in f", {b},"
    assert OUTFIT_B_MANIFEST_MARKER not in a
    assert OUTFIT_B_MANIFEST_MARKER not in b
    assert_no_test_markers(a)
    assert_no_test_markers(b)


def test_p01_includes_hand_on_head() -> None:
    p = prompt_p01_hand_on_head(_ADOPTED)
    assert "hand on top of head" in p
    assert "palm flat on scalp" in p
    assert OUTFIT_B_MANIFEST_MARKER not in p
