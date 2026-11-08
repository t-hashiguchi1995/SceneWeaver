import json

import pytest
from PIL import Image

from creator_studio.application.lettering.fonts import resolve_font
from creator_studio.application.lettering.models import LetteringLayer, LetteringLayout
from creator_studio.application.lettering.planner import plan_layout
from creator_studio.application.lettering.quality import evaluate_layout
from creator_studio.application.lettering.quality_store import load_evaluation, save_evaluation
from creator_studio.application.lettering.renderer import render_lettering

FACE = {"id": "face1", "role": "face", "bbox_xyxy_norm": (0.33, 0.04, 0.67, 0.32)}


def regression():
    return LetteringLayout(
        "regression",
        "",
        {"width": 1536, "height": 1536},
        [
            LetteringLayer(
                "speech_bubble",
                "speech",
                "台詞",
                bbox_xyxy_norm=(0.02, 0.02, 0.172, 0.476),
                anchor_xy_norm=(0.50, 0.20),
                font_px=43,
                fit_feasible=True,
            )
        ],
    )


def summary(label, result):
    print(
        json.dumps(
            {
                "fixture": label,
                "final_gate": result["final_gate"],
                **{k: result[k]["status"] for k in ("gate_a", "gate_b", "gate_c", "gate_d")},
                "score": result["gate_b"]["score"],
                "components": result["gate_b"]["components"],
            }
        )
    )


def test_face_tail_regression():
    result = evaluate_layout(regression(), 1536, 1536, [FACE])
    assert result["gate_a"]["status"] == "FAIL"
    hit = next(f for f in result["gate_a"]["findings"] if f["code"] == "face_tail_intrusion")
    assert hit["intersection_px"] > 0
    assert hit["bbox_xyxy_norm"][0] == pytest.approx(0.33)
    assert result["final_gate"] == "FAIL"
    assert result["gate_b"]["components"]["tail"] < 60
    summary(1, result)


def test_missing_regions():
    result = evaluate_layout(regression(), 1536, 1536)
    assert result["gate_a"]["status"] == "UNKNOWN"
    assert result["gate_a"]["reason"] == "missing_protected_regions"
    assert result["final_gate"] != "PASS"


def test_clean_demo():
    layout = plan_layout(
        image_w=1536,
        image_h=1536,
        blocks=[
            {
                "kind": "speech_bubble",
                "text": "ぜ、全部脱いだよ……。手で隠すのが精一杯……",
                "anchor_xy_norm": (0.50, 0.20),
            },
            {"kind": "inner_voice", "text": "……はずかしい、見ないで……"},
        ],
        protected_regions_norm=[FACE["bbox_xyxy_norm"]],
    )
    render_lettering(Image.new("RGB", (1536, 1536), "white"), layout)
    print({v.block_id: v.font_resolved for v in layout.layers})
    result = evaluate_layout(layout, 1536, 1536, [FACE])
    assert result["gate_a"]["status"] == "PASS"
    assert result["gate_b"]["score"] is not None
    assert result["final_gate"] == "REVIEW"
    assert "not_evaluated_p0" in result["reasons"]
    summary(3, result)


def test_legacy_missing_font_and_roundtrip(tmp_path):
    layout = regression()
    layer = layout.layers[0]
    layer.font_px = None
    layer.tail_mode = "none"
    result = evaluate_layout(layout, 1536, 1536)
    assert result["gate_b"]["status"] == "UNKNOWN"
    assert result["gate_b"]["score"] is None
    assert result["gate_b"]["components"]["tail"] is None
    save_evaluation(result, directory=tmp_path)
    assert load_evaluation(result["quality_evaluation_id"], directory=tmp_path) == result
    with pytest.raises(FileNotFoundError):
        load_evaluation("../escape", directory=tmp_path)


@pytest.mark.parametrize("font,expected", [(22, 100), (20, 75), (17, 40)])
def test_font_bands(font, expected):
    layout = regression()
    layout.layers[0].font_resolved = resolve_font(layout.layers[0]).to_dict()
    layout.layers[0].font_px = font
    layout.layers[0].tail_mode = "none"
    assert evaluate_layout(layout, 1000, 1000)["gate_b"]["components"]["typography"] == expected


def test_overflow_and_interference():
    layout = regression()
    layout.layers.append(LetteringLayer.from_dict({**layout.layers[0].to_dict(), "block_id": "b"}))
    layout.warnings = ["text_overflow:speech"]
    result = evaluate_layout(layout, 1536, 1536)
    codes = {f["code"]: f["severity"] for f in result["gate_a"]["findings"]}
    assert codes == {"text_overflow": "critical", "text_interference": "major"}
    assert result["gate_a"]["status"] == "FAIL"


def test_pixel_geometry_boundary_and_generic_penalty():
    layer = LetteringLayer(
        "speech_bubble",
        "a",
        "text",
        shape="rect",
        bbox_xyxy_norm=(0.1, 0.1, 0.2, 0.2),
        anchor_xy_norm=(0.4, 0.15),
        font_px=24,
        fit_feasible=True,
    )
    layout = LetteringLayout("pixels", "", {"width": 1000, "height": 500}, [layer])
    region = {"role": "face", "bbox_xyxy_norm": (0.3, 0.15, 0.4, 0.3)}
    result = evaluate_layout(layout, 1000, 500, [region])
    assert result["gate_a"]["status"] == "PASS"  # Tail runs along the boundary.
    region["bbox_xyxy_norm"] = (0.3, 0.1, 0.4, 0.2)
    region["role"] = "protected"
    baseline = evaluate_layout(layout, 1000, 500, [])
    crossed = evaluate_layout(layout, 1000, 500, [region])
    assert crossed["gate_a"]["status"] == "PASS"
    assert crossed["gate_b"]["components"]["tail"] == pytest.approx(
        max(0, baseline["gate_b"]["components"]["tail"] - 25)
    )
    region["role"] = "face"
    face = evaluate_layout(layout, 1000, 500, [region])
    hit = face["gate_a"]["findings"][0]
    assert hit["intersection_px"] == pytest.approx(100)


def test_na_redistribution_and_component_floor():
    layer = LetteringLayer(
        "narration", "a", "text", bbox_xyxy_norm=(0.1, 0.1, 0.2, 0.2), font_px=17, fit_feasible=True
    )
    layer.font_resolved = resolve_font(layer).to_dict()
    layout = LetteringLayout("floor", "", {"width": 1000, "height": 1000}, [layer])
    result = evaluate_layout(layout, 1000, 1000)
    assert result["gate_b"]["score"] == 85
    assert result["gate_b"]["status"] == "REVIEW"  # Typography is below 75.
    assert result["gate_b"]["components"]["tail"] is None


def test_missing_bounds_are_unmeasured():
    layout = regression()
    layout.layers[0].bbox_xyxy_norm = None
    result = evaluate_layout(layout, 1536, 1536, [FACE])
    assert result["gate_a"]["status"] == "UNKNOWN"
    assert result["gate_b"]["score"] is None
    assert result["gate_b"]["components"]["shape"] is None
