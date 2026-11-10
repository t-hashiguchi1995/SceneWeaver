"""Deterministic P0 measurements. IDs and timestamps are evaluation metadata only."""

import math
from datetime import UTC, datetime
from itertools import combinations
from uuid import uuid4

from .fonts import KIND_DEFAULTS, canonical_profile, font_cmap
from .planner import overlap, segment_interior_length, tail_start

# Provisional thresholds; calibrate against reviewed manga pages before production use.
PROFILES = {
    "manga_single_character_v1": {
        # Length / min(canvas): <=8%, <=12%, <=15%, <=20%, then 15.
        "tail_bands": ((0.08, 100), (0.12, 85), (0.15, 60), (0.20, 35)),
        "tail_good": 0.08,
        "tail_bad": 0.15,
        "aspect_good": 3.0,
        "aspect_bad": 4.5,
        "height_good": 0.38,
        "font_good": 0.022,
        "font_review": 0.018,
        "pass": 85,
        "review": 70,
        "component_floor": 75,
        "weights": {
            "protection": 30,
            "tail": 20,
            "typography": 20,
            "reading_order": 15,
            "shape": 15,
        },
    }
}


def _clip(start, end, box):
    """Return the interior intersection endpoints, excluding boundary-only contact."""
    if segment_interior_length(start, end, box) <= 0:
        return None
    lo, hi = 0.0, 1.0
    for a, b, lower, upper in zip(start, end, box[:2], box[2:]):
        if b != a:
            t1, t2 = sorted(((lower - a) / (b - a), (upper - a) / (b - a)))
            lo, hi = max(lo, t1), min(hi, t2)
    return [tuple(a + t * (b - a) for a, b in zip(start, end)) for t in (lo, hi)]


def evaluate_layout(
    layout, image_w, image_h, protected_regions=None, profile="manga_single_character_v1"
):
    """Evaluate stored geometry and font evidence without fitting text.

    Protection sums smaller-box overlap percentages (clamped to 0..100).
    Tail uses the worst piecewise length score, minus 25 for any generic crossing.
    Typography averages stored fit/font bands; absent font evidence is UNKNOWN.
    Reading order penalizes each inversion by 25, using (center_y, -center_x).
    Shape averages aspect interpolation and a 20-point excessive-height penalty.
    Only N/A weights are redistributed; missing evidence never receives a score.
    """
    if image_w <= 0 or image_h <= 0:
        raise ValueError("Image dimensions must be positive")
    p = PROFILES[profile]
    regions = protected_regions or []
    findings, reasons, tails, fonts, shapes = [], [], [], [], []
    font_records = []
    profile_mismatch = False
    protection_loss, face_hit = 0.0, False
    any_generic_crossing = False
    scale = (image_w, image_h, image_w, image_h)
    px = lambda box: tuple(a * d for a, d in zip(box, scale))
    norm = lambda box: [a / d for a, d in zip(box, scale)]
    speech = [v for v in layout.layers if v.kind == "speech_bubble"]
    solo = len({v.speaker_id for v in speech}) == 1
    text_layers = [v for v in layout.layers if v.text]

    def finding(code, layer, region=None, intersection=None, box=None, severity="critical"):
        if region is not None:
            region = dict(region)
            if "bbox_xyxy_norm" in region:
                region["bbox_xyxy_norm"] = list(region["bbox_xyxy_norm"])
        findings.append(
            {
                "code": code,
                "severity": severity,
                "layer_id": layer.block_id,
                "region": region,
                "intersection_px": intersection,
                "bbox_xyxy_norm": norm(box) if box else None,
                "source": "deterministic",
            }
        )

    for layer in layout.layers:
        box = px(layer.bbox_xyxy_norm) if layer.bbox_xyxy_norm else None
        if box is None:
            reasons.append("missing_bbox:" + layer.block_id)
        overflow = (
            layer.fit_feasible is False
            or layer.text_overflow
            or any(
                f"{code}:{layer.block_id}" in layout.warnings
                for code in ("text_overflow", "no_feasible_layout")
            )
        )
        if overflow:
            finding("text_overflow", layer, box=box)
        tip = layer.tail_tip_xy_norm or layer.anchor_xy_norm
        has_tail = (
            layer.kind == "speech_bubble"
            and layer.tail_mode == "auto"
            and layer.tail_variant != "none"
            and tip
        )
        start = end = None
        if has_tail and box:
            end = tuple(a * d for a, d in zip(tip, scale))
            start = tail_start(box, end)
            ratio = math.dist(start, end) / min(image_w, image_h)
            # Tight tail bands: 8%, 12%, 15%, 20% of the shorter canvas side.
            score = next(
                (score for limit, score in p["tail_bands"] if ratio <= limit + 1e-12),
                15,
            )
            tails.append(score)
            if ratio > 0.15:
                finding("tail_too_long", layer, severity="major")
                findings[-1]["ratio"] = ratio
        elif layer.kind == "speech_bubble" and layer.tail_variant == "none":
            tails.append(100 if solo else 70)
        generic_crossing = False
        for region in regions:
            rbox = px(region["bbox_xyxy_norm"])
            area = overlap(box, rbox) if box else 0
            face = region.get("role") == "face"
            if area > 0:
                if face:
                    face_hit = True
                    intersection = (
                        max(box[0], rbox[0]),
                        max(box[1], rbox[1]),
                        min(box[2], rbox[2]),
                        min(box[3], rbox[3]),
                    )
                    finding("face_bubble_intrusion", layer, region, area, intersection)
                else:
                    protection_loss += 100 * area / min(overlap(box, box), overlap(rbox, rbox))
            clipped = _clip(start, end, rbox) if start is not None else None
            if clipped:
                if face:
                    face_hit = True
                    a, b = clipped
                    finding(
                        "face_tail_intrusion",
                        layer,
                        region,
                        math.dist(a, b),
                        (min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])),
                    )
                else:
                    generic_crossing = True
        any_generic_crossing = any_generic_crossing or generic_crossing
        if layer.text:
            resolved = layer.font_resolved
            if resolved:
                font_records.append(
                    {
                        "layer_id": layer.block_id,
                        **{
                            k: resolved[k]
                            for k in (
                                "profile",
                                "font_name",
                                "font_version",
                                "font_file",
                                "fallback",
                            )
                        },
                    }
                )
                cmap = font_cmap(resolved["font_path"])
                missing = sorted({c for c in layer.text if c not in "\n\r" and ord(c) not in cmap})
                if missing:
                    finding("missing_glyph", layer)
                    findings[-1]["chars"] = missing
                if (
                    resolved["profile"] != KIND_DEFAULTS[layer.kind]
                    and canonical_profile(layer.font_profile) != resolved["profile"]
                ):
                    finding("font_profile_mismatch", layer, severity="major")
                    profile_mismatch = True
            if not resolved or layer.font_px is None:
                fonts.append(None)
                reasons.append("missing_font_info:" + layer.block_id)
            else:
                ratio = layer.font_px / min(image_w, image_h)
                fonts.append(
                    0
                    if overflow
                    else 100
                    if ratio >= p["font_good"]
                    else 75
                    if ratio >= p["font_review"]
                    else 40
                )
        if box:
            width, height = box[2] - box[0], box[3] - box[1]
            aspect = max(width / height, height / width)
            score = max(
                0,
                100 - 60 * max(0, aspect - p["aspect_good"]) / (p["aspect_bad"] - p["aspect_good"]),
            ) - (20 if height / image_h > p["height_good"] else 0)
            shapes.append(max(0, score) if layer.shape == "oval" else 100)
    for a, b in combinations(text_layers, 2):
        if a.bbox_xyxy_norm and b.bbox_xyxy_norm:
            ab, bb = px(a.bbox_xyxy_norm), px(b.bbox_xyxy_norm)
            area = overlap(ab, bb)
            if area > 0:
                finding(
                    "text_interference",
                    a,
                    {"layer_id": b.block_id},
                    area,
                    (max(ab[0], bb[0]), max(ab[1], bb[1]), min(ab[2], bb[2]), min(ab[3], bb[3])),
                    "major",
                )
    if not regions and any(
        v.kind == "speech_bubble"
        and v.tail_mode == "auto"
        and v.tail_variant != "none"
        and (v.anchor_xy_norm or v.tail_tip_xy_norm)
        for v in layout.layers
    ):
        reasons.append("missing_protected_regions")
    critical = any(v["severity"] == "critical" for v in findings)
    a_status = (
        "FAIL"
        if critical
        else "UNKNOWN"
        if any(r.startswith(("missing_protected", "missing_bbox")) for r in reasons)
        else "PASS"
    )
    ordered = sorted(text_layers, key=lambda v: v.reading_order)

    def position(v):
        x1, y1, x2, y2 = v.bbox_xyxy_norm
        return ((y1 + y2) / 2, -(x1 + x2) / 2)

    inversions = sum(
        position(a) > position(b)
        for a, b in combinations(ordered, 2)
        if a.bbox_xyxy_norm and b.bbox_xyxy_norm
    )
    components = {
        "protection": 0 if face_hit else max(0, 100 - protection_loss),
        "tail": max(0, min(tails) - (25 if any_generic_crossing else 0)) if tails else None,
        "typography": None if not fonts or None in fonts else sum(fonts) / len(fonts),
        "reading_order": max(0, 100 - 25 * inversions),
        "shape": sum(shapes) / len(shapes) if shapes else None,
    }
    if profile_mismatch and components["typography"] is not None:
        components["typography"] = min(60, components["typography"])
    if any(r.startswith("missing_bbox:") for r in reasons):
        # No partial geometry score may masquerade as a complete measurement.
        for name in ("protection", "tail", "reading_order", "shape"):
            components[name] = None
    if not fonts:
        reasons.append("missing_font_info")
    unknown = any(r.startswith(("missing_font", "missing_bbox")) for r in reasons)
    weights = p["weights"]
    measured = {k: v for k, v in components.items() if v is not None}
    total = (
        None
        if unknown
        else sum(weights[k] * v for k, v in measured.items()) / sum(weights[k] for k in measured)
    )
    b_status = (
        "UNKNOWN"
        if total is None
        else "FAIL"
        if total < p["review"]
        else "PASS"
        if total >= p["pass"] and min(measured.values()) >= p["component_floor"]
        else "REVIEW"
    )
    c = {"status": "UNKNOWN", "score": None, "reason": "not_evaluated_p0"}
    d = {"status": "UNKNOWN", "reason": "not_evaluated_p0"}
    final = (
        "FAIL"
        if "FAIL" in (a_status, b_status)
        else "PASS"
        if all(s == "PASS" for s in (a_status, b_status, c["status"], d["status"]))
        else "REVIEW"
    )
    reasons = list(
        dict.fromkeys([v["code"] for v in findings] + reasons + [c["reason"], d["reason"]])
    )
    return {
        "quality_evaluation_id": "qe_" + uuid4().hex[:12],
        "layout_id": layout.layout_id,
        "image": {"w": image_w, "h": image_h},
        "profile": profile,
        "protocol_version": "lettering-qg-p0-0.1",
        "gate_a": dict(
            status=a_status,
            findings=findings,
            **(
                {"reason": "missing_protected_regions"}
                if "missing_protected_regions" in reasons
                else {}
            ),
        ),
        "gate_b": {"status": b_status, "score": total, "components": components},
        "gate_c": c,
        "gate_d": d,
        "final_gate": final,
        "reasons": reasons,
        "fonts": font_records,
        "evaluator_versions": {
            "lettering_quality": "0.1.0",
            "profile": profile,
            "font_registry": "0.1.0",
        },
        "created_at": datetime.now(UTC).isoformat(),
    }
