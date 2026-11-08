from creator_studio.application.lettering.planner import overlap, plan_layout


def test_nonoverlap():
    layout = plan_layout(
        image_w=800, image_h=600, blocks=[{"text": "こんにちは", "kind": "speech_bubble"}] * 2
    )
    assert overlap(*(v.bbox_xyxy_norm for v in layout.layers)) == 0


def test_protected():
    protected = (0.5, 0, 1, 0.5)
    layout = plan_layout(
        image_w=800,
        image_h=600,
        blocks=[{"text": "台詞", "kind": "speech_bubble"}],
        protected_regions_norm=[protected],
    )
    assert overlap(layout.layers[0].bbox_xyxy_norm, protected) == 0


def test_infeasible():
    layout = plan_layout(
        image_w=80,
        image_h=60,
        blocks=[{"text": "長い台詞" * 100, "kind": "speech_bubble", "block_id": "long"}],
    )
    assert "no_feasible_layout:long" in layout.warnings


def test_demo_oval_width_and_fit(tmp_path):
    from PIL import Image

    from creator_studio.application.image.speech_bubble import find_japanese_font
    from creator_studio.application.lettering.planner import fit_text, font_target
    from creator_studio.application.lettering.renderer import render_lettering

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
        protected_regions_norm=[(0.33, 0.04, 0.67, 0.32)],
    )
    bubble = layout.layers[0]
    x1, y1, x2, y2 = bubble.bbox_xyxy_norm
    assert 0.15 <= x2 - x1 <= 0.30
    assert (y2 - y1) / (x2 - x1) <= 4.5
    size, _, feasible, _ = fit_text(
        bubble,
        round(x2 * 1536) - round(x1 * 1536),
        round(y2 * 1536) - round(y1 * 1536),
        font_target(1536, bubble),
        find_japanese_font(),
    )
    assert feasible and size == font_target(1536, bubble)
    assert not layout.warnings
    output = render_lettering(Image.new("RGB", (1536, 1536), "#808080"), layout)
    output.save(tmp_path / "lettering-demo.png")
    print("demo bbox:", bubble.bbox_xyxy_norm, "warnings:", layout.warnings)
