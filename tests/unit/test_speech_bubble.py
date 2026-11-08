from io import BytesIO

import pytest
from PIL import Image, ImageChops

from creator_studio.application.image import speech_bubble


def image_bytes() -> bytes:
    output = BytesIO()
    Image.new("RGB", (800, 600), "#336699").save(output, format="PNG")
    return output.getvalue()


@pytest.mark.parametrize("position", sorted(speech_bubble.POSITIONS))
def test_composite_preserves_dimensions_and_changes_selected_corner(position):
    source = image_bytes()
    result = speech_bubble.composite_speech_bubble(source, "こんにちは！", position)
    with Image.open(BytesIO(result)) as image, Image.open(BytesIO(source)) as original:
        assert image.format == "PNG"
        assert image.size == original.size
        diff = ImageChops.difference(image.convert("RGB"), original)
        bounds = diff.getbbox()
        assert bounds is not None
        x0, y0, x1, y1 = bounds
        assert (x0 > 400) if position.endswith("right") else (x1 < 400)
        assert (y1 < 300) if position.startswith("top") else (y0 > 300)


def test_long_japanese_text_fits(tmp_path):
    source = tmp_path / "source.png"
    source.write_bytes(image_bytes())
    text = "これは長い日本語の台詞です。" * 30
    result = speech_bubble.composite_speech_bubble(source, text)
    with Image.open(BytesIO(result)) as image:
        assert image.size == (800, 600)
        image.load()
    font, lines, width, height, pad, tail, advance = speech_bubble.bubble_layout(
        text, speech_bubble.find_japanese_font(), 800, 600
    )
    assert font.size < 800 // 28
    assert height + tail <= 600 * 0.30
    assert len(lines) * advance + 2 * pad == height
    assert all(font.getlength(line) <= width - 2 * pad for line in lines)


@pytest.mark.parametrize("text,position", [("台詞", "center"), ("  \n", "top-right")])
def test_invalid_spec(text, position):
    with pytest.raises(ValueError):
        speech_bubble.composite_speech_bubble(image_bytes(), text, position)


def test_missing_font_is_clear(monkeypatch, tmp_path):
    monkeypatch.setattr(speech_bubble, "FONT_ROOTS", (tmp_path,))
    with pytest.raises(RuntimeError, match="Japanese-capable font"):
        speech_bubble.composite_speech_bubble(image_bytes(), "こんにちは")
