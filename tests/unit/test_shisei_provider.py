from creator_studio.infrastructure.reference.shisei_provider import ShiseiPoseProvider


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
