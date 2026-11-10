"""Bounded deterministic placement with protected-region and tail geometry scoring."""

import math
from dataclasses import asdict, is_dataclass
from uuid import uuid4

from PIL import ImageFont

from creator_studio.application.lettering.models import LetteringLayer, LetteringLayout
from creator_studio.application.lettering.vertical_text import layout_horizontal, layout_vertical

from .fonts import resolve_font


def overlap(a, b):
    return max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))


def segment_interior_length(start, end, box):
    """Length inside an open rectangle; boundary contact is not crossing."""
    low, high = 0.0, 1.0
    for a, b, lo, hi in zip(start, end, box[:2], box[2:]):
        d = b - a
        if abs(d) < 1e-14:
            if not lo < a < hi:
                return 0.0
        else:
            t1, t2 = sorted(((lo - a) / d, (hi - a) / d))
            low, high = max(low, t1), min(high, t2)
    return max(0.0, high - low) * math.dist(start, end)


def tail_start(box, tip):
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    dx, dy = tip[0] - cx, tip[1] - cy
    radius = math.hypot(dx / ((box[2] - box[0]) / 2), dy / ((box[3] - box[1]) / 2))
    return (cx + dx / radius, cy + dy / radius) if radius > 1 else tip


def safe_tip(anchor, regions):
    tip = anchor
    for x1, y1, x2, y2 in regions:
        if x1 < tip[0] < x2 and y1 < tip[1] < y2:
            tip = min(
                ((x1, tip[1]), (x2, tip[1]), (tip[0], y1), (tip[0], y2)),
                key=lambda p: math.dist(p, tip),
            )
    return tip


OVAL_INSET = (0.72, 0.84)


def text_insets(layer, width, height):
    if layer.shape == "oval":
        return width * (1 - OVAL_INSET[0]) / 2, height * (1 - OVAL_INSET[1]) / 2
    return 0, 0


def fit_text(layer, width, height, target, font_path):
    ix, iy = text_insets(layer, width, height)
    width, height = width - 2 * ix, height - 2 * iy
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
    m = max(0.01, margin_norm)
    # Preserve caller order: the first protected box is face-critical. All
    # interior crossings are ranked before soft costs, including face crossings.
    protected_regions_norm = [tuple(p) for p in protected_regions_norm]
    blocks = [asdict(b) if is_dataclass(b) else dict(b) for b in blocks]
    speech = [b for b in blocks if b["kind"] == "speech_bubble"]
    solo = len(speech) == 1 or len({b.get("speaker_id") for b in speech}) == 1
    region_w, region_h = (0.5 - 2 * m) * image_w, (0.5 - 2 * m) * image_h
    for index, block in enumerate(blocks):
        data = asdict(block) if is_dataclass(block) else dict(block)
        data.setdefault("block_id", f"block_{index + 1}")
        data["reading_order"] = index
        layer = LetteringLayer.from_dict(data)
        layer.font_resolved = resolve_font(layer).to_dict()
        font_path = layer.font_resolved["font_path"]
        target = font_target(image_h, layer)
        max_width, max_height = region_w, region_h
        if layer.shape == "oval" and layer.writing_mode == "vertical-rl":
            max_width = min(region_w, 0.30 * image_w)
            max_height = min(region_h, 4.5 * max_width)
        fits = []
        for attempt in range(32):
            fit_height = max_height - attempt * target * 1.12
            if fit_height <= 0:
                break
            size, lines, feasible, pad = fit_text(layer, max_width, fit_height, target, font_path)
            advance = size * 1.12
            if layer.writing_mode == "vertical-rl":
                bw = len(lines) * advance + 2 * pad
                bh = max(map(len, lines), default=1) * advance + 2 * pad
            else:
                font = ImageFont.truetype(str(font_path), size)
                bw = max((font.getlength(v) for v in lines), default=1) + 2 * pad
                bh = len(lines) * size * 1.4 + 2 * pad
            if layer.shape == "oval":
                # Invert the renderer inset and round outward to preserve wrapping.
                bw = math.ceil(bw / OVAL_INSET[0]) + 2
                bh = math.ceil(bh / OVAL_INSET[1]) + 2
            if layer.shape == "oval" and layer.writing_mode == "vertical-rl":
                bw = max(bw, min(max_width, bh / 3))
            fits.append((not feasible, bh / bw, bw, bh, feasible))
            if not (layer.shape == "oval" and layer.writing_mode == "vertical-rl") or (
                feasible and bh / bw <= 3.2
            ):
                break
        chosen = fits[-1] if fits[-1][0] is False and fits[-1][1] <= 3.2 else min(fits)
        _, aspect, bw, bh, feasible = chosen
        if layer.shape == "oval" and layer.writing_mode == "vertical-rl" and aspect > 3.2:
            result.warnings.append(f"high_aspect:{layer.block_id}")
        bw, bh = min(max_width, bw) / image_w, min(max_height, bh) / image_h
        layer.tail_tip_xy_norm = None
        if layer.kind == "speech_bubble" and layer.tail_mode == "auto" and layer.anchor_xy_norm:
            layer.tail_tip_xy_norm = safe_tip(layer.anchor_xy_norm, protected_regions_norm)
        positions = [
            (1 - m - bw if right else m, y)
            for right, y in (
                (True, m),
                (False, m),
                (True, 1 - m - bh),
                (False, 1 - m - bh),
                (True, (1 - bh) / 2),
                (False, (1 - bh) / 2),
            )
        ]
        positions += [
            (m + ix * 0.04, m + iy * 0.04)
            for iy in range(25)
            for ix in range(25)
            if m + ix * 0.04 + bw <= 1 - m + 1e-12 and m + iy * 0.04 + bh <= 1 - m + 1e-12
        ]
        candidates = []
        seen = set()
        unique_positions = []
        for position in positions:
            if position not in seen:
                seen.add(position)
                unique_positions.append(position)
        boxes = []
        for x, y in unique_positions[:600]:
            box = (x, y, x + bw, y + bh)
            if x < m - 1e-12 or y < m - 1e-12 or box[2] > 1 - m + 1e-12 or box[3] > 1 - m + 1e-12:
                continue
            protected = sum(overlap(box, p) for p in protected_regions_norm)
            boxes.append((box, protected))
        # Protected bubble overlap is a hard constraint. If no clean box exists,
        # minimize overlap first, then use the usual costs to break ties.
        clean_boxes = [(box, protected) for box, protected in boxes if protected == 0]
        if clean_boxes:
            boxes = clean_boxes
        else:
            least_overlap = min(protected for _, protected in boxes)
            boxes = [(box, protected) for box, protected in boxes if protected == least_overlap]
        for box, protected in boxes:
            x, y = box[:2]
            placed = sum(overlap(box, p.bbox_xyxy_norm) for p in result.layers)
            full_tip = layer.tail_tip_xy_norm
            variants = [("none", None)]
            if full_tip is not None:
                start = tail_start(box, full_tip)
                length = math.hypot(
                    (full_tip[0] - start[0]) * image_w,
                    (full_tip[1] - start[1]) * image_h,
                )
                fraction = min(1, 0.08 * min(image_w, image_h) / length) if length else 1
                short_tip = tuple(a + fraction * (b - a) for a, b in zip(start, full_tip))
                variants += [("short", short_tip), ("full", full_tip)]
            for variant, tip in variants:
                # Crossing ranks ahead of all soft preferences, including clarity.
                preference = (
                    {"none": -0.12, "short": -0.06, "full": 0}[variant]
                    if solo
                    else (0.15 if variant == "none" and full_tip else 0)
                )
                crossing = (
                    sum(
                        segment_interior_length(tail_start(box, tip), tip, p)
                        for p in protected_regions_norm
                    )
                    if tip
                    else 0
                )
                margin_bonus = 0.0001 if min(x, y, 1 - box[2], 1 - box[3]) >= 0.02 - 1e-12 else 0
                # Keep crossings primary; discourage long tails in pixel space.
                tail_ratio = (
                    math.dist(
                        tuple(a * d for a, d in zip(tail_start(box, tip), (image_w, image_h))),
                        tuple(a * d for a, d in zip(tip, (image_w, image_h))),
                    )
                    / min(image_w, image_h)
                    if tip
                    else 0
                )
                anchor_distance = (
                    math.hypot(
                        ((box[0] + box[2]) / 2 - layer.anchor_xy_norm[0]) * image_w,
                        ((box[1] + box[3]) / 2 - layer.anchor_xy_norm[1]) * image_h,
                    )
                    / min(image_w, image_h)
                    if tip and layer.anchor_xy_norm
                    else 0
                )
                tail_cost = (
                    0.01 * anchor_distance
                    + 0.5 * max(0, tail_ratio - 0.12)
                    + 3 * max(0, tail_ratio - 0.20)
                )
                candidates.append(
                    (
                        crossing,
                        100 * crossing
                        + 3 * protected
                        + 2 * placed
                        + tail_cost
                        - margin_bonus
                        + preference,
                        box,
                        protected,
                        variant,
                        tip,
                    )
                )
        # Ambiguity is unavoidable when no clean drawn tail is available.
        if not solo and not any(c[4] != "none" and c[0] <= 1e-12 for c in candidates):
            candidates = [
                (
                    crossing,
                    cost - (0.15 if variant == "none" and layer.tail_tip_xy_norm else 0),
                    box,
                    protected,
                    variant,
                    tip,
                )
                for crossing, cost, box, protected, variant, tip in candidates
            ]
        crosses, _, layer.bbox_xyxy_norm, protected, variant, tip = min(
            candidates, key=lambda c: (c[0] > 1e-12, c[0] if c[0] > 1e-12 else 0, c[1])
        )
        if layer.kind == "speech_bubble":
            layer.tail_variant = variant
            layer.tail_tip_xy_norm = tip
        left, top, right, bottom = layer.bbox_xyxy_norm
        layer.font_px, _, layer.fit_feasible, _ = fit_text(
            layer,
            round(right * image_w) - round(left * image_w),
            round(bottom * image_h) - round(top * image_h),
            target,
            font_path,
        )
        feasible = feasible and layer.fit_feasible
        layer.fit_feasible = feasible
        if crosses > 1e-12:
            result.warnings.append(f"tail_crosses_protected:{layer.block_id}")
        if not feasible:
            result.warnings.append(f"no_feasible_layout:{layer.block_id}")
        if protected > 0:
            result.warnings.append(f"overlap_protected:{layer.block_id}")
        result.layers.append(layer)
    return result
