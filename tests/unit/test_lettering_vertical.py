from creator_studio.application.lettering.vertical_text import layout_vertical


def fit(text, **kwargs):
    return layout_vertical(text, font_px=24, box_w_px=200, box_h_px=54, min_font_px=24, **kwargs)


def test_columns():
    assert fit("あいうえお").columns == ["あい", "うえ", "お"]


def test_kinsoku_push():
    assert fit("あい。う").columns == ["あい。", "う"]


def test_kinsoku_pull():
    assert fit("あ「いう").columns == ["あ", "「い", "う"]


def test_shrink():
    result = layout_vertical("あいうえおか", font_px=32, box_w_px=55, box_h_px=80, min_font_px=21)
    assert result.feasible and 21 <= result.font_px < 32


def test_tiny():
    result = layout_vertical("長い台詞" * 20, font_px=24, box_w_px=5, box_h_px=5)
    assert not result.feasible and result.font_px == 21


def test_full_kinsoku_boundaries():
    from creator_studio.application.lettering.vertical_text import (
        END_FORBIDDEN,
        START_FORBIDDEN,
        _columns,
    )

    for text in (
        "あい……。うえ",
        "あいーうえ",
        "あ(いう)え",
        "あ［いう］え",
        "あいゃうえ",
        "あい―うえ",
    ):
        columns = _columns(text, 2)
        assert "".join(columns) == text
        assert all(c[0] not in START_FORBIDDEN and c[-1] not in END_FORBIDDEN for c in columns)


def test_explicit_paragraph_edges_use_spacers():
    from creator_studio.application.lettering.vertical_text import (
        END_FORBIDDEN,
        START_FORBIDDEN,
        _columns,
    )

    columns = _columns("。あ\nい「", 2)
    assert all(c[0] not in START_FORBIDDEN and c[-1] not in END_FORBIDDEN for c in columns)
    assert "".join(columns).replace("　", "") == "。あい「"
