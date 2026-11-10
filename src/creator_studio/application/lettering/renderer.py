"""Pillow lettering with canvas-clipped tails and bounded text tiles."""

import math

from PIL import Image, ImageDraw, ImageFont

from creator_studio.application.lettering.planner import fit_text, font_target, text_insets

from .fonts import resolve_font

ROTATED = set("ー―－…‥〜～:：;；()（）[]［］{}｛｝「」『』【】〔〕〈〉《》")


def glyph_tile(char, font, fill="black", stroke_width=0, stroke_fill="white"):
    """Transform a glyph within its square cell."""
    size = font.size
    box = font.getbbox(char, stroke_width=stroke_width)
    ink = Image.new("RGBA", (max(1, box[2] - box[0]), max(1, box[3] - box[1])))
    ImageDraw.Draw(ink).text(
        (-box[0], -box[1]),
        char,
        font=font,
        fill=fill,
        stroke_width=stroke_width,
        stroke_fill=stroke_fill,
    )
    if char in "、。" and ink.getbbox():
        ink = ink.crop(ink.getbbox())
    if ink.width > size or ink.height > size:
        ink.thumbnail((size, size))
    tile = Image.new("RGBA", (size, size))
    xy = (
        (size - ink.width, 0)
        if char in "、。"
        else ((size - ink.width) // 2, (size - ink.height) // 2)
    )
    tile.alpha_composite(ink, xy)
    return tile.transpose(Image.Transpose.ROTATE_270) if char in ROTATED else tile


def _shape(draw, layer, w, h, size, anchor):
    if min(w, h) < 7:
        if layer.shape != "none":
            draw.rectangle((0, 0, w - 1, h - 1), fill="black" if layer.shape == "rect" else "white")
        return
    box = (2, 2, w - 3, h - 3)
    if layer.shape == "oval":
        draw.ellipse(box, fill="white", outline="black", width=3)
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


def tail_base_width(length_px, canvas_min_px):
    """Scale the 9..30 px base band from the 1536 px reference canvas."""
    scale = canvas_min_px / 1536
    return max(9 * scale, min(30 * scale, 0.30 * length_px))


def _tail(draw, layer, w, h, size, anchor, origin, canvas_min_px):
    if (
        layer.tail_mode == "none"
        or layer.tail_variant == "none"
        or layer.shape != "oval"
        or min(w, h) < 7
    ):
        return
    if anchor is not None and (
        ((anchor[0] - w / 2) / max(1, w / 2 - 3)) ** 2
        + ((anchor[1] - h / 2) / max(1, h / 2 - 3)) ** 2
        > 1
    ):
        cx, cy = w / 2, h / 2
        dx, dy = anchor[0] - cx, anchor[1] - cy
        angle = math.atan2(dy / max(1, h / 2 - 3), dx / max(1, w / 2 - 3))
        rx, ry = w / 2 - 4, h / 2 - 4
        edge = (cx + rx * math.cos(angle), cy + ry * math.sin(angle))
        base_px = tail_base_width(math.dist(edge, anchor), canvas_min_px)
        # Solve for an ellipse chord with the requested pixel width.
        chord_radius = math.hypot(rx * math.sin(angle), ry * math.cos(angle))
        delta = math.asin(min(1, base_px / (2 * chord_radius)))
        base = [
            (cx + rx * math.cos(a), cy + ry * math.sin(a)) for a in (angle - delta, angle + delta)
        ]
        base = [(x + origin[0], y + origin[1]) for x, y in base]
        anchor = (anchor[0] + origin[0], anchor[1] + origin[1])
        # Polygon outlines stay inside the triangle, preserving all pixels
        # outside the bubble bounds and tail polygon.
        draw.polygon([base[0], anchor, base[1]], fill="white", outline="black", width=3)
        draw.line(base, fill="white", width=4)


def render_lettering(base_image, layout):
    result = base_image.convert("RGB").copy()
    cell_boxes = {}
    result.info["glyph_cell_boxes"] = cell_boxes
    width, height = result.size
    for layer in sorted(layout.layers, key=lambda v: v.reading_order):
        layer.font_resolved = resolve_font(layer).to_dict()
        font_path = layer.font_resolved["font_path"]
        cell_boxes[layer.block_id] = []
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
        size, lines, feasible, pad = fit_text(layer, w, h, font_target(height, layer), font_path)
        layer.font_px, layer.fit_feasible = size, feasible
        font = ImageFont.truetype(str(font_path), size)
        tip = layer.tail_tip_xy_norm or layer.anchor_xy_norm
        anchor = None if tip is None else (tip[0] * width - left, tip[1] * height - top)
        _shape(draw, layer, w, h, size, None)
        tail = Image.new("RGBA", result.size)
        _tail(ImageDraw.Draw(tail), layer, w, h, size, anchor, (left, top), min(width, height))
        inset_x, inset_y = text_insets(layer, w, h)
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
                    x, y = w - inset_x - pad - size - col * advance, inset_y + pad + row * advance
                    cell_boxes[layer.block_id].append(
                        (char, left + round(x), top + round(y), size, size)
                    )
                    if halo:
                        halo_glyph = glyph_tile(char, font, (255, 255, 255, 140))
                        for dx, dy in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
                            tile.alpha_composite(halo_glyph, (round(x + dx), round(y + dy)))
                    tile.alpha_composite(glyph, (round(x), round(y)))
        else:
            for i, line in enumerate(lines):
                xy = (inset_x + pad, inset_y + pad + i * size * 1.4)
                if halo:
                    for dx, dy in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
                        draw.text(
                            (xy[0] + dx, xy[1] + dy),
                            line,
                            font=font,
                            fill=(255, 255, 255, 140),
                            anchor="lt",
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
        result.paste(tail, (0, 0), tail)
    return result
