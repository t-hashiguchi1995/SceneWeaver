import json

from creator_studio.application.lettering.models import LetteringLayer, LetteringLayout
from creator_studio.application.lettering.store import load_layout, save_layout


def test_roundtrip(tmp_path):
    layer = LetteringLayer(
        "inner_voice",
        "b",
        "こんにちは",
        speaker_id="s",
        bbox_xyxy_norm=(0.1, 0.2, 0.3, 0.4),
        anchor_xy_norm=(0.5, 0.6),
        shape="cloud",
        reading_order=2,
        font_profile="custom",
        min_font_px=23,
    )
    layout = LetteringLayout(
        "layout", "asset", {"width": 800, "height": 600}, [layer], warnings=["warning"], revision=3
    )
    assert LetteringLayout.from_dict(json.loads(json.dumps(layout.to_dict()))) == layout
    save_layout(layout, directory=tmp_path)
    assert load_layout("layout", directory=tmp_path) == layout
