from itertools import combinations

import pytest
from PIL import Image, ImageFont

from creator_studio.application.lettering.fonts import font_cmap, resolve_font
from creator_studio.application.lettering.models import LetteringLayer, LetteringLayout
from creator_studio.application.lettering.quality import evaluate_layout
from creator_studio.application.lettering.renderer import glyph_tile, render_lettering


def test_resolution():
    speech = resolve_font(LetteringLayer("speech_bubble", "a", "台詞"))
    assert speech.font_file == "GenEiAntiqueNv6-M.ttf"
    assert not speech.fallback and "6.0" in speech.font_version
    assert resolve_font(LetteringLayer("narration", "b", "text")).fallback
    for kind, profile in (("inner_voice", "manga_inner"), ("sfx", "manga_sfx")):
        resolution = resolve_font(LetteringLayer(kind, kind, "あ"))
        assert resolution.profile == profile and resolution.fallback
    alias = LetteringLayer("speech_bubble", "a", "", font_profile="jp_manga_sans")
    assert resolve_font(alias) == speech


def test_vertical_cells_and_comma():
    layer = LetteringLayer(
        "speech_bubble",
        "a",
        "あー、……。『テスト』（笑）っゃ…ー",
        bbox_xyxy_norm=(0.1, 0.1, 0.9, 0.9),
        shape="none",
        min_font_px=40,
    )
    layout = LetteringLayout("test", "", {"width": 800, "height": 800}, [layer])
    output = render_lettering(Image.new("RGB", (800, 800), "white"), layout)
    boxes = output.info["glyph_cell_boxes"]["a"]
    assert "".join(b[0] for b in boxes) == layer.text
    for a, b in combinations(boxes, 2):
        assert (
            a[1] + a[3] <= b[1] or b[1] + b[3] <= a[1] or a[2] + a[4] <= b[2] or b[2] + b[4] <= a[2]
        )
    font = ImageFont.truetype(resolve_font(layer).font_path, 40)
    tile = glyph_tile("、", font)
    alpha = tile.getchannel("A")
    mass = sum(alpha.getpixel((x, y)) for y in range(40) for x in range(40))
    cx = sum(x * alpha.getpixel((x, y)) for y in range(40) for x in range(40)) / mass
    cy = sum(y * alpha.getpixel((x, y)) for y in range(40) for x in range(40)) / mass
    assert cx > 20 and cy < 20


def test_missing_glyph():
    layer = LetteringLayer(
        "speech_bubble", "a", "", font_px=40, bbox_xyxy_norm=(0.1, 0.1, 0.3, 0.3), tail_mode="none"
    )
    layer.font_resolved = resolve_font(layer).to_dict()
    cmap = font_cmap(layer.font_resolved["font_path"])
    layer.text = next((c for c in ["🐤", "🦄", "𰻞"] if ord(c) not in cmap), "")
    if not layer.text:
        pytest.skip("All candidate characters are present")
    result = evaluate_layout(LetteringLayout("test", "", {}, [layer]), 1000, 1000)
    assert result["gate_a"]["status"] == "FAIL"
    hit = next(f for f in result["gate_a"]["findings"] if f["code"] == "missing_glyph")
    assert hit["chars"] == [layer.text]


def test_profile_mismatch_and_explicit_override():
    layer = LetteringLayer(
        "speech_bubble",
        "a",
        "台詞",
        font_px=40,
        bbox_xyxy_norm=(0.1, 0.1, 0.3, 0.3),
        tail_mode="none",
    )
    layer.font_resolved = resolve_font(LetteringLayer("narration", "b", "")).to_dict()
    layout = LetteringLayout("test", "", {}, [layer])
    result = evaluate_layout(layout, 1000, 1000)
    assert any(f["code"] == "font_profile_mismatch" for f in result["gate_a"]["findings"])
    assert result["gate_b"]["components"]["typography"] <= 60
    layer.font_profile = "narration"
    assert not evaluate_layout(layout, 1000, 1000)["gate_a"]["findings"]


def test_legacy_font_px_is_unmeasured():
    layer = LetteringLayer(
        "narration", "a", "台詞", font_px=40, bbox_xyxy_norm=(0.1, 0.1, 0.3, 0.3)
    )
    result = evaluate_layout(LetteringLayout("test", "", {}, [layer]), 1000, 1000)
    assert result["gate_b"]["components"]["typography"] is None
    assert result["gate_b"]["status"] == "UNKNOWN"
