import math

import pytest
from PIL import Image, ImageChops, ImageDraw, ImageFont

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
        anchor_xy_norm=(0.95, 0.5),
    )
    output = render_lettering(
        source, LetteringLayout("l", "a", {"width": 400, "height": 400}, [layer])
    )
    assert output.size == source.size and output.mode == "RGB"
    assert ImageChops.difference(source, output).getbbox() is not None
    for box in ((0, 0, 400, 80), (0, 320, 400, 400), (0, 80, 80, 320), (320, 80, 400, 320)):
        if shape == "oval" and box == (320, 80, 400, 320):
            # The external tail is allowed in this strip, but nowhere else.
            assert any(max(output.getpixel((x, 200))) < 40 for x in range(330, 380))
        else:
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


def test_tail_outside_bbox_preserves_unrelated_pixels():
    source = Image.new("RGB", (400, 400), "#808080")
    layer = LetteringLayer(
        "speech_bubble",
        "b",
        "",
        bbox_xyxy_norm=(0.1, 0.2, 0.5, 0.8),
        anchor_xy_norm=(0.9, 0.5),
    )
    output = render_lettering(
        source, LetteringLayout("l", "a", {"width": 400, "height": 400}, [layer])
    )
    assert any(max(output.getpixel((x, y))) < 40 for x in range(210, 350) for y in range(185, 215))
    # The horizontal tail's two base points lie on the inset ellipse.
    allowed = Image.new("L", source.size)
    mask = ImageDraw.Draw(allowed)
    mask.rectangle((40, 80, 199, 319), fill=255)
    mask.polygon(
        [
            (120 + 76 * math.cos(0.05), 200 - 116 * math.sin(0.05)),
            (360, 200),
            (120 + 76 * math.cos(0.05), 200 + 116 * math.sin(0.05)),
        ],
        fill=255,
    )
    for y in range(400):
        for x in range(400):
            if not allowed.getpixel((x, y)):
                assert output.getpixel((x, y)) == source.getpixel((x, y))


@pytest.mark.parametrize("text", ["あ" * 20, "ぜ、全部脱いだよ……。手で隠すのが精一杯……"])
def test_planned_oval_text_stays_inside_ellipse(text):
    from creator_studio.application.lettering.planner import plan_layout

    source = Image.new("RGB", (1536, 1536), "#808080")
    layout = plan_layout(
        image_w=1536,
        image_h=1536,
        blocks=[
            {"kind": "speech_bubble", "text": text},
        ],
    )
    output = render_lettering(source, layout)
    layer = layout.layers[0]
    layer.text = ""
    blank = render_lettering(source, layout)
    left, top, right, bottom = [round(v * 1536) for v in layer.bbox_xyxy_norm]
    cx, cy = (left + right - 1) / 2, (top + bottom - 1) / 2
    rx, ry = (right - left - 5) / 2 - 5, (bottom - top - 5) / 2 - 5
    text_pixels = 0
    for y in range(top, bottom):
        for x in range(left, right):
            if max(output.getpixel((x, y))) < 40 and output.getpixel((x, y)) != blank.getpixel(
                (x, y)
            ):
                text_pixels += 1
                assert ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1
    assert text_pixels > 100


def test_stored_tip_and_tail_none():
    source = Image.new("RGB", (400, 400), "blue")
    layer = LetteringLayer(
        "speech_bubble",
        "b",
        "",
        bbox_xyxy_norm=(0.1, 0.2, 0.5, 0.8),
        anchor_xy_norm=(0.95, 0.5),
        tail_tip_xy_norm=(0.7, 0.5),
    )
    layout = LetteringLayout("l", "a", {"width": 400, "height": 400}, [layer])
    output = render_lettering(source, layout)
    assert output.getpixel((279, 200)) != source.getpixel((279, 200))
    assert output.getpixel((350, 200)) == source.getpixel((350, 200))
    layer.tail_mode = "none"
    output = render_lettering(source, layout)
    assert output.getpixel((250, 200)) == source.getpixel((250, 200))
