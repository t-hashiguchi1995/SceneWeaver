"""Pillow lettering, clipped to each editable layer's bounds."""

import math

from PIL import Image, ImageDraw, ImageFont

from creator_studio.application.image.speech_bubble import find_japanese_font
from creator_studio.application.lettering.planner import fit_text, font_target

ROTATED = set("ー―…‥「」『』（）")


def glyph_tile(char, font, fill="black", stroke_width=0, stroke_fill="white"):
    """Tight glyph tile; clockwise rotation preserves visible glyph bounds."""
    box = font.getbbox(char, stroke_width=stroke_width)
    tile = Image.new("RGBA", (max(1, box[2] - box[0]), max(1, box[3] - box[1])))
    ImageDraw.Draw(tile).text(
        (-box[0], -box[1]),
        char,
        font=font,
        fill=fill,
        stroke_width=stroke_width,
        stroke_fill=stroke_fill,
    )
    return tile.rotate(-90, expand=True) if char in ROTATED else tile


def _shape(draw, layer, w, h, size, anchor):
    if min(w, h) < 7:
        if layer.shape != "none":
            draw.rectangle((0, 0, w - 1, h - 1), fill="black" if layer.shape == "rect" else "white")
        return
    box = (2, 2, w - 3, h - 3)
    if layer.shape == "oval":
        draw.ellipse(box, fill="white", outline="black", width=3)
        if anchor is not None and (
            ((anchor[0] - w / 2) / max(1, w / 2 - 3)) ** 2
            + ((anchor[1] - h / 2) / max(1, h / 2 - 3)) ** 2
            > 1
        ):
            cx, cy = w / 2, h / 2
            dx, dy = anchor[0] - cx, anchor[1] - cy
            angle = math.atan2(dy / max(1, h / 2 - 3), dx / max(1, w / 2 - 3))
            delta = min(0.25, size * 0.5 / max(w, h))
            base = [
                (cx + (w / 2 - 4) * math.cos(a), cy + (h / 2 - 4) * math.sin(a))
                for a in (angle - delta, angle + delta)
            ]
            draw.polygon([base[0], anchor, base[1]], fill="white")
            draw.line([base[0], anchor, base[1]], fill="black", width=3)
            draw.line(base, fill="white", width=4)
    elif layer.shape == "rect":
        draw.rectangle(box, fill="black")
    elif layer.shape == "jagged":
        points = []
        for i in range(32):
            a, r = i * math.pi / 16, 1 if i % 2 == 0 else 0.82
            points.append(
                (w / 2 + (w / 2 - 3) * r * math.cos(a), h / 2 + (h / 2 - 3) * r * math.sin(a))
            )
        draw.polygon(points, fill="white", outline="black", width=3)
    elif layer.shape == "cloud":
        radius = max(3, min(w, h) * 0.15)
        circles = [
            (
                w / 2 + (w / 2 - radius - 4) * math.cos(i * math.pi / 8),
                h / 2 + (h / 2 - radius - 4) * math.sin(i * math.pi / 8),
            )
            for i in range(16)
        ]
        for extra, color in ((3, "black"), (0, "white")):
            for x, y in circles:
                r = radius + extra
                draw.ellipse((x - r, y - r, x + r, y + r), fill=color)
            draw.ellipse((radius, radius, w - radius, h - radius), fill=color)


def render_lettering(base_image, layout):
    result = base_image.convert("RGB").copy()
    font_path = find_japanese_font()
    width, height = result.size
    for layer in sorted(layout.layers, key=lambda v: v.reading_order):
        if layer.bbox_xyxy_norm is None:
            continue
        x1, y1, x2, y2 = layer.bbox_xyxy_norm
        left, top, right, bottom = (
            round(x1 * width),
            round(y1 * height),
            round(x2 * width),
            round(y2 * height),
        )
        w, h = right - left, bottom - top
        if w < 1 or h < 1:
            continue
        tile = Image.new("RGBA", (w, h))
        draw = ImageDraw.Draw(tile)
        size, lines, _, pad = fit_text(layer, w, h, font_target(height, layer), font_path)
        font = ImageFont.truetype(str(font_path), size)
        anchor = (
            None
            if layer.anchor_xy_norm is None
            else (layer.anchor_xy_norm[0] * width - left, layer.anchor_xy_norm[1] * height - top)
        )
        _shape(draw, layer, w, h, size, anchor)
        color = (
            "white"
            if layer.shape == "rect"
            else "#333333"
            if layer.kind == "inner_voice"
            else "black"
        )
        stroke = 3 if layer.kind == "sfx" else 0
        halo = layer.kind == "inner_voice" and layer.shape == "none"
        if layer.writing_mode == "vertical-rl":
            advance = size * 1.12
            for col, line in enumerate(lines):
                for row, char in enumerate(line):
                    glyph = glyph_tile(char, font, color, stroke, "white")
                    x, y = w - pad - size - col * advance, pad + row * advance
                    if char in "。、":
                        x, y = x + size * 0.32, y - size * 0.32
                    if halo:
                        halo_glyph = glyph_tile(char, font, "white")
                        for dx, dy in ((-2, -2), (-2, 2), (2, -2), (2, 2)):
                            tile.alpha_composite(halo_glyph, (round(x + dx), round(y + dy)))
                    tile.alpha_composite(glyph, (round(x), round(y)))
        else:
            for i, line in enumerate(lines):
                xy = (pad, pad + i * size * 1.4)
                if halo:
                    for dx, dy in ((-2, -2), (-2, 2), (2, -2), (2, 2)):
                        draw.text(
                            (xy[0] + dx, xy[1] + dy), line, font=font, fill="white", anchor="lt"
                        )
                draw.text(
                    xy,
                    line,
                    font=font,
                    fill=color,
                    anchor="lt",
                    stroke_width=stroke,
                    stroke_fill="white",
                )
        result.paste(tile, (left, top), tile)
    return result
