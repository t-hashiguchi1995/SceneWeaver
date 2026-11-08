import pytest
from PIL import Image, ImageChops, ImageFont

from creator_studio.application.image.speech_bubble import find_japanese_font
from creator_studio.application.lettering.models import LetteringLayer, LetteringLayout
from creator_studio.application.lettering.renderer import glyph_tile, render_lettering


@pytest.mark.parametrize("shape", ["oval", "cloud", "jagged", "rect", "none"])
def test_shapes_and_clip(shape):
    source = Image.new("RGB", (400, 400), "blue")
    layer = LetteringLayer(
        "inner_voice" if shape == "none" else "speech_bubble",
        "b",
        "こんにちは。ー",
        shape=shape,
        bbox_xyxy_norm=(0.2, 0.2, 0.8, 0.8),
        anchor_xy_norm=(0.79, 0.79),
    )
    output = render_lettering(
        source, LetteringLayout("l", "a", {"width": 400, "height": 400}, [layer])
    )
    assert output.size == source.size and output.mode == "RGB"
    assert ImageChops.difference(source, output).getbbox() is not None
    for box in ((0, 0, 400, 80), (0, 320, 400, 400), (0, 80, 80, 320), (320, 80, 400, 320)):
        assert source.crop(box).tobytes() == output.crop(box).tobytes()


def test_rotated_dash():
    tile = glyph_tile("ー", ImageFont.truetype(str(find_japanese_font()), 40))
    bounds = tile.getbbox()
    assert bounds[3] - bounds[1] > bounds[2] - bounds[0]


@pytest.mark.parametrize("mode", ["horizontal", "vertical-rl"])
def test_sfx(mode):
    layer = LetteringLayer(
        "sfx", "b", "ドーン", writing_mode=mode, bbox_xyxy_norm=(0.1, 0.1, 0.9, 0.9)
    )
    assert render_lettering(
        Image.new("RGB", (400, 400)),
        LetteringLayout("l", "a", {"width": 400, "height": 400}, [layer]),
    ).size == (400, 400)


def test_tail_reaches_anchor_inside_layer_bounds():
    source = Image.new("RGB", (400, 400), "blue")
    layer = LetteringLayer("speech_bubble", "b", "", bbox_xyxy_norm=(0.2, 0.2, 0.8, 0.8))
    layout = LetteringLayout("l", "a", {"width": 400, "height": 400}, [layer])
    plain = render_lettering(source, layout)
    layer.anchor_xy_norm = (0.79, 0.79)
    tailed = render_lettering(source, layout)
    assert plain.getpixel((315, 315)) == (0, 0, 255)
    assert tailed.getpixel((315, 315)) != (0, 0, 255)


def test_tiny_manual_bounds_do_not_crash():
    for shape in ("oval", "cloud", "jagged", "rect", "none"):
        layer = LetteringLayer(
            "speech_bubble", "b", "台詞", shape=shape, bbox_xyxy_norm=(0, 0, 0.01, 0.01)
        )
        output = render_lettering(
            Image.new("RGB", (100, 100)),
            LetteringLayout("l", "a", {"width": 100, "height": 100}, [layer]),
        )
        assert output.size == (100, 100)
