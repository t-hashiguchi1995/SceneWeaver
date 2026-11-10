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


def test_demo_face_and_body_are_hard_constraints():
    regions = [(0.33, 0.04, 0.67, 0.32), (0.30, 0.28, 0.86, 1.00)]
    kwargs = {
        "image_w": 1536,
        "image_h": 1536,
        "blocks": [
            {
                "block_id": "b01",
                "kind": "speech_bubble",
                "text": "ぜ、全部脱いだよ……。手で隠すのが精一杯……",
                "anchor_xy_norm": (0.50, 0.20),
            },
            {"block_id": "b02", "kind": "inner_voice", "text": "……はずかしい、見ないで……"},
        ],
        "protected_regions_norm": regions,
    }
    layout = plan_layout(**kwargs)
    bubble = layout.layers[0]
    assert all(overlap(bubble.bbox_xyxy_norm, region) == 0 for region in regions)
    assert "overlap_protected:b01" not in layout.warnings
    repeated = plan_layout(**kwargs)
    assert bubble.bbox_xyxy_norm == repeated.layers[0].bbox_xyxy_norm
    assert bubble.tail_tip_xy_norm == repeated.layers[0].tail_tip_xy_norm
    print("face+body bbox:", bubble.bbox_xyxy_norm, "tail tip:", bubble.tail_tip_xy_norm)


def test_cramped_layout_falls_back_to_least_overlap():
    # Only a narrow strip is unprotected, too small for any candidate.
    region = (0.10, 0, 1, 1)
    layout = plan_layout(
        image_w=1536,
        image_h=1536,
        blocks=[
            {
                "block_id": "b01",
                "kind": "speech_bubble",
                "text": "ぜ、全部脱いだよ……。手で隠すのが精一杯……",
                "anchor_xy_norm": (0.50, 0.20),
            }
        ],
        protected_regions_norm=[region],
    )
    assert len(layout.layers) == 1
    bubble = layout.layers[0]
    assert overlap(bubble.bbox_xyxy_norm, region) > 0
    assert "overlap_protected:b01" in layout.warnings
    # The leftmost candidate has minimum intrusion, despite the distant anchor.
    assert bubble.bbox_xyxy_norm[0] == 0.02


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
    assert (y2 - y1) / (x2 - x1) <= 3.2
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
    from creator_studio.application.lettering.planner import segment_interior_length, tail_start

    face = (0.33, 0.04, 0.67, 0.32)
    assert overlap(bubble.bbox_xyxy_norm, face) == 0
    if bubble.tail_tip_xy_norm is not None:
        assert (
            segment_interior_length(
                tail_start(bubble.bbox_xyxy_norm, bubble.tail_tip_xy_norm),
                bubble.tail_tip_xy_norm,
                face,
            )
            < 1e-12
        )
    for layer in layout.layers:
        a, b, c, d = layer.bbox_xyxy_norm
        assert min(a, b, 1 - c, 1 - d) >= 0.01
    bubble.text = ""
    blank = render_lettering(Image.new("RGB", (1536, 1536), "#808080"), layout)
    left, top, right, bottom = [round(v * 1536) for v in bubble.bbox_xyxy_norm]
    cx, cy = (left + right - 1) / 2, (top + bottom - 1) / 2
    rx, ry = (right - left - 5) / 2 - 5, (bottom - top - 5) / 2 - 5
    count = 0
    for y in range(top, bottom):
        for x in range(left, right):
            pixel = output.getpixel((x, y))
            if max(pixel) < 40 and pixel != blank.getpixel((x, y)):
                count += 1
                assert ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1
    assert count > 100
    print(
        "demo bbox:",
        bubble.bbox_xyxy_norm,
        "tail tip:",
        bubble.tail_tip_xy_norm,
        "warnings:",
        layout.warnings,
    )


def test_tail_none_and_unavoidable_crossing():
    from creator_studio.application.lettering.planner import segment_interior_length

    assert segment_interior_length((0, 0), (1, 0), (0, 0, 1, 1)) == 0
    layout = plan_layout(
        image_w=800,
        image_h=800,
        blocks=[{"kind": "speech_bubble", "text": "台詞", "anchor_xy_norm": (0.5, 0.5)}],
        protected_regions_norm=[(0, 0, 1, 1)],
    )
    assert layout.layers[0].tail_variant == "none"
    assert "tail_crosses_protected:block_1" not in layout.warnings
    layout = plan_layout(
        image_w=800,
        image_h=800,
        blocks=[
            {
                "kind": "speech_bubble",
                "text": "台詞",
                "anchor_xy_norm": (0.5, 0.5),
                "tail_mode": "none",
            }
        ],
    )
    assert layout.layers[0].tail_tip_xy_norm is None


def test_grid_finds_space_between_protected_edges():
    regions = [(0, 0, 0.2, 1), (0.8, 0, 1, 1)]
    kwargs = {
        "image_w": 800,
        "image_h": 800,
        "blocks": [{"kind": "speech_bubble", "text": "台詞"}],
        "protected_regions_norm": regions,
    }
    first, second = plan_layout(**kwargs), plan_layout(**kwargs)
    assert first.layers[0].bbox_xyxy_norm == second.layers[0].bbox_xyxy_norm
    assert not first.warnings
    assert all(overlap(first.layers[0].bbox_xyxy_norm, p) == 0 for p in regions)
