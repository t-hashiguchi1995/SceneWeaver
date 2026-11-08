"""Deterministic corner-first placement, with explicit overlap warnings."""

from dataclasses import asdict, is_dataclass
from uuid import uuid4

from PIL import ImageFont

from creator_studio.application.image.speech_bubble import find_japanese_font
from creator_studio.application.lettering.models import LetteringLayer, LetteringLayout
from creator_studio.application.lettering.vertical_text import layout_horizontal, layout_vertical


def overlap(a, b):
    return max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))


def fit_text(layer, width, height, target, font_path):
    padding = max(4, target * 0.65)
    width, height = max(1, width - 2 * padding), max(1, height - 2 * padding)
    if layer.writing_mode == "vertical-rl":
        fitted = layout_vertical(
            layer.text,
            font_px=target,
            box_w_px=width,
            box_h_px=height,
            min_font_px=layer.min_font_px,
        )
        return fitted.font_px, fitted.columns, fitted.feasible, padding
    size = max(target, layer.min_font_px)
    while True:
        font = ImageFont.truetype(str(font_path), size)
        lines = layout_horizontal(layer.text, font, width)
        feasible = (
            len(lines) * size * 1.4 <= height
            and max((font.getlength(v) for v in lines), default=0) <= width
        )
        if feasible or size == layer.min_font_px:
            return size, lines, feasible, padding
        size = max(layer.min_font_px, size - 2)


def font_target(image_h, layer):
    return max(
        layer.min_font_px,
        round(max(24, int(image_h * 0.028)) * (1.6 if layer.kind == "sfx" else 1)),
    )


def plan_layout(*, image_w, image_h, blocks, protected_regions_norm=(), margin_norm=0.02):
    if image_w <= 0 or image_h <= 0 or not 0 <= margin_norm < 0.25:
        raise ValueError("Invalid canvas or margin")
    result = LetteringLayout(uuid4().hex, "", {"width": image_w, "height": image_h})
    font_path = find_japanese_font()
    m = margin_norm
    region_w, region_h = (0.5 - 2 * m) * image_w, (0.5 - 2 * m) * image_h
    for index, block in enumerate(blocks):
        data = asdict(block) if is_dataclass(block) else dict(block)
        data.setdefault("block_id", f"block_{index + 1}")
        data["reading_order"] = index
        layer = LetteringLayer.from_dict(data)
        target = font_target(image_h, layer)
        size, lines, feasible, pad = fit_text(layer, region_w, region_h, target, font_path)
        advance = size * 1.12
        if layer.writing_mode == "vertical-rl":
            bw = len(lines) * advance + 2 * pad
            bh = max(map(len, lines), default=1) * advance + 2 * pad
        else:
            font = ImageFont.truetype(str(font_path), size)
            bw = max((font.getlength(v) for v in lines), default=1) + 2 * pad
            bh = len(lines) * size * 1.4 + 2 * pad
        bw, bh = min(region_w, bw) / image_w, min(region_h, bh) / image_h
        candidates = []
        for right, y in (
            (True, m),
            (False, m),
            (True, 1 - m - bh),
            (False, 1 - m - bh),
            (True, (1 - bh) / 2),
            (False, (1 - bh) / 2),
        ):
            x = 1 - m - bw if right else m
            box = (x, y, x + bw, y + bh)
            protected = sum(overlap(box, p) for p in protected_regions_norm)
            placed = sum(overlap(box, p.bbox_xyxy_norm) for p in result.layers)
            outside = bw * bh - overlap(box, (0, 0, 1, 1))
            candidates.append((3 * protected + 2 * placed + 5 * max(0, outside), box, protected))
        _, layer.bbox_xyxy_norm, protected = min(candidates, key=lambda c: c[0])
        if not feasible:
            result.warnings.append(f"no_feasible_layout:{layer.block_id}")
        if protected > 0:
            result.warnings.append(f"overlap_protected:{layer.block_id}")
        result.layers.append(layer)
    return result
