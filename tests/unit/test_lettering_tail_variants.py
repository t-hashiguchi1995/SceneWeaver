import math

import pytest
from PIL import Image

from creator_studio.application.lettering.models import LetteringLayer, LetteringLayout
from creator_studio.application.lettering.planner import overlap, plan_layout, tail_start
from creator_studio.application.lettering.quality import evaluate_layout
from creator_studio.application.lettering.renderer import render_lettering, tail_base_width


def test_solo_demo_tail_summary():
    regions = [(0.33, 0.04, 0.67, 0.32), (0.30, 0.28, 0.86, 1.00)]
    layout = plan_layout(
        image_w=1536,
        image_h=1536,
        blocks=[
            {
                "kind": "speech_bubble",
                "speaker_id": "solo",
                "text": "ぜ、全部脱いだよ……。手で隠すのが精一杯……",
                "anchor_xy_norm": (0.50, 0.20),
            },
            {"kind": "inner_voice", "text": "……はずかしい、見ないで……"},
        ],
        protected_regions_norm=regions,
    )
    bubble = layout.layers[0]
    assert bubble.tail_variant in {"none", "short"}
    if bubble.tail_tip_xy_norm:
        assert (
            math.dist(
                tail_start(bubble.bbox_xyxy_norm, bubble.tail_tip_xy_norm), bubble.tail_tip_xy_norm
            )
            <= 0.08 + 1e-12
        )
    assert all(
        overlap(layer.bbox_xyxy_norm, region) == 0 for layer in layout.layers for region in regions
    )
    result = evaluate_layout(
        layout,
        1536,
        1536,
        [
            {"role": "face" if i == 0 else "protected", "bbox_xyxy_norm": r}
            for i, r in enumerate(regions)
        ],
    )
    assert result["gate_a"]["status"] == "PASS"
    assert result["gate_b"]["components"]["tail"] >= 85
    print(
        {
            "variant": bubble.tail_variant,
            "final_gate": result["final_gate"],
            "gate_b": result["gate_b"]["score"],
            "tail": result["gate_b"]["components"]["tail"],
        }
    )


def test_multiple_speakers_keep_clean_tails():
    region = (0.45, 0.4, 0.55, 0.6)
    layout = plan_layout(
        image_w=1536,
        image_h=768,
        blocks=[
            {
                "kind": "speech_bubble",
                "text": "こんにちは",
                "speaker_id": speaker,
                "anchor_xy_norm": anchor,
            }
            for speaker, anchor in [("a", (0.35, 0.25)), ("b", (0.65, 0.75))]
        ],
        protected_regions_norm=[region],
    )
    assert all(layer.tail_variant in {"short", "full"} for layer in layout.layers)
    assert not layout.warnings
    for layer in layout.layers:
        assert overlap(layer.bbox_xyxy_norm, region) == 0
    assert overlap(*[layer.bbox_xyxy_norm for layer in layout.layers]) == 0


@pytest.mark.parametrize(
    "ratio,expected",
    [
        (0.08, 100),
        (0.10, 85),
        (0.12, 85),
        (0.14, 60),
        (0.15, 60),
        (0.18, 35),
        (0.20, 35),
        (0.30, 15),
    ],
)
def test_tail_bands(ratio, expected):
    layer = LetteringLayer(
        "speech_bubble",
        "a",
        "",
        bbox_xyxy_norm=(0.1, 0.1, 0.3, 0.3),
        tail_tip_xy_norm=(0.3 + ratio, 0.2),
        tail_variant="full",
    )
    layout = LetteringLayout("bands", "", {"width": 1536, "height": 1536}, [layer])
    result = evaluate_layout(layout, 1536, 1536)
    assert result["gate_b"]["components"]["tail"] == expected
    findings = [f for f in result["gate_a"]["findings"] if f["code"] == "tail_too_long"]
    assert bool(findings) == (ratio > 0.15)
    if findings:
        assert findings[0]["severity"] == "major"
        assert findings[0]["ratio"] == pytest.approx(ratio)


@pytest.mark.parametrize("speakers,expected", [(["a"], 100), (["a", "b"], 70)])
def test_tail_none_speaker_clarity_and_rendering(speakers, expected):
    layers = [
        LetteringLayer(
            "speech_bubble",
            str(i),
            "",
            speaker_id=s,
            bbox_xyxy_norm=(0.1, 0.1 + i * 0.4, 0.3, 0.3 + i * 0.4),
            anchor_xy_norm=(0.9, 0.5),
            tail_variant="none",
        )
        for i, s in enumerate(speakers)
    ]
    layout = LetteringLayout("none", "", {"width": 1536, "height": 1536}, layers)
    assert evaluate_layout(layout, 1536, 1536)["gate_b"]["components"]["tail"] == expected
    image = Image.new("RGB", (1536, 1536), "blue")
    rendered = render_lettering(image, layout)
    for layer in layers:
        layer.tail_mode = "none"
    assert rendered.tobytes() == render_lettering(image, layout).tobytes()
    assert LetteringLayout.from_dict(layout.to_dict()).layers[0].tail_variant == "none"


def test_tail_base_width_and_polygon():
    from creator_studio.application.lettering.renderer import _tail

    class Drawing:
        def polygon(self, points, **kwargs):
            self.points = points

        def line(self, *args, **kwargs):
            pass

    draw = Drawing()
    layer = LetteringLayer("speech_bubble", "a", "", tail_variant="full")
    _tail(draw, layer, 300, 400, 43, (300 + 0.30 * 1536, 200), (0, 0), 1536)
    assert math.dist(draw.points[0], draw.points[2]) == pytest.approx(30)
    assert tail_base_width(0.30 * 1536, 1536) >= 9
