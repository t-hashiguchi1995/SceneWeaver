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
