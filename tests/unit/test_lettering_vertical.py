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
