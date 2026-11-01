from creator_studio.infrastructure.reference.shisei_provider import ShiseiPoseProvider


def test_shisei_semantics_match_sitting_line_art() -> None:
    """A3 Human FAIL root cause: standing labels on seated bytes must not recur."""
    provider = ShiseiPoseProvider()
    for pose in provider.list_poses():
        cats = {c.lower() for c in pose.categories}
        assert "standing" not in cats, f"{pose.id} still categorized standing"
        assert "sitting" in cats or "seated" in cats, f"{pose.id} missing sitting category"
        assert "standing" not in pose.label.lower(), f"{pose.id} label still says Standing"
        for angle, view in pose.views.items():
            prompt = (view.prompt or "").lower()
            assert "standing" not in prompt, f"{pose.id}/{angle} prompt still standing"
            assert "sitting" in prompt or "seated" in prompt, f"{pose.id}/{angle} not seated"
            assert view.line is not None


def test_shisei_provider_loads_pack() -> None:
    provider = ShiseiPoseProvider()
    poses = provider.list_poses()
    assert len(poses) >= 3
    first = poses[0]
    assert first.id.startswith("sw-pose-")
    assert first.source.provider == "shisei"
    assert first.source.license == "CC0-1.0"
    # Must not expose ai-pose-gallery naming
    assert "std_P" not in first.label
    assert "P001" not in first.label


def test_shisei_one_pose_has_three_views() -> None:
    provider = ShiseiPoseProvider()
    multi = next(p for p in provider.list_poses() if len(p.available_views()) >= 3)
    assert "front" in multi.views
    assert multi.views["front"].line is not None
    path = provider.resolve_asset_path(multi.views["front"].line.relative_path)
    assert path is not None and path.is_file()


def test_shisei_rejects_path_traversal() -> None:
    provider = ShiseiPoseProvider()
    assert provider.resolve_asset_path("../etc/passwd") is None
    assert provider.resolve_asset_path("/etc/passwd") is None
