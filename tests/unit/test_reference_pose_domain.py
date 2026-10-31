from creator_studio.domain.reference import PoseDefinition, PoseRefAsset, PoseSource, PoseView


def test_pose_definition_available_views_order() -> None:
    pose = PoseDefinition(
        id="sw-pose-0001",
        label="Standing pose 001",
        categories=("standing",),
        tags=("standing",),
        people_count=1,
        content_rating="general",
        default_view="front",
        views={
            "side": PoseView(id="a", angle="side", prompt="p"),
            "front": PoseView(id="b", angle="front", prompt="p"),
            "diag": PoseView(id="c", angle="diag", prompt="p"),
        },
        source=PoseSource(provider="shisei", version="0.3.0", license="CC0-1.0"),
    )
    assert pose.available_views() == ["front", "diag", "side"]
    assert pose.thumbnail_relative_path() is None  # no line asset


def test_pose_ref_asset_fields() -> None:
    ref = PoseRefAsset(relative_path="sw-pose-0001/front.webp", sha256="abc", mime="image/webp")
    assert ref.asset_id is None
