from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock, call

import pytest

from creator_studio.adapters.eagle.errors import EagleError, EagleErrorCode
from creator_studio.application.integrations.eagle_sync import (
    SyncAssetToEagle,
    build_annotation,
    build_tags,
    to_windows_path,
)
from creator_studio.domain.asset.models import Asset, AssetKind


class Gateway:
    def __init__(self):
        self.folders = []
        self.items = []
        self.created = []
        self.added = []

    def list_folders(self):
        return self.folders

    def create_folder(self, name, parent_id):
        self.created.append((name, parent_id))
        return {"id": name, "name": name}

    def list_items(self, *, limit=200, offset=0):
        return self.items[offset : offset + limit]

    def add_from_path(self, **payload):
        self.added.append(payload)
        self.items.append({"id": "item", "annotation": payload["annotation"]})
        return {"id": "item"}


class Uow:
    def __init__(self, asset, attempts):
        self.assets = SimpleNamespace(get=lambda asset_id: asset)
        self.generation_attempts = SimpleNamespace(list_for_shot=lambda shot_id: attempts)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


@pytest.fixture
def setup_sync(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "creator_studio.application.integrations.eagle_sync.load_eagle_config",
        lambda: {"enabled": True},
    )
    monkeypatch.setattr(
        "creator_studio.application.integrations.eagle_sync.to_windows_path",
        lambda path: r"D:\image.png",
    )
    path = tmp_path / "image.png"
    path.write_bytes(b"image")
    asset = Asset.create(
        sha256="a",
        uri="asset://a/image.png",
        kind=AssetKind.GENERATED,
        mime="image/png",
        byte_size=5,
        metadata={"review_decision": "adopted"},
        provenance={"shot_id": "shot"},
    )
    gateway = Gateway()
    store = SimpleNamespace(path_for_uri=lambda uri: path)
    uow = Uow(asset, [])
    return SyncAssetToEagle(uow, gateway, store), asset, gateway, uow


def test_annotation_and_tags(setup_sync):
    _, asset, _, _ = setup_sync
    assert build_annotation(asset, None) == f"sw_asset:{asset.id} | sw_attempt:- | seed:-\n-\n-"
    asset.metadata.update(character_name="Alice", preset_id="p")
    assert build_tags(asset) == ["sceneweaver", "status:adopted", "char:Alice", "preset:p"]
    attempt = SimpleNamespace(
        id="a",
        seed=0,
        payload={"nested": [{"edited_positive": "1girl, smile", "negative_prompt": "blur"}]},
    )
    assert build_annotation(asset, attempt) == (
        f"sw_asset:{asset.id} | sw_attempt:a | seed:0\n1girl, smile\nblur"
    )


def test_sync_creates_folders(setup_sync, monkeypatch):
    service, asset, gateway, uow = setup_sync
    sleep = Mock()
    monkeypatch.setattr("creator_studio.application.integrations.eagle_sync.time.sleep", sleep)
    uow.generation_attempts.list_for_shot = lambda shot_id: [
        SimpleNamespace(id="a", seed=42, payload={"positive": "smile"}, output_asset_ids=[asset.id])
    ]
    result = service.execute(asset.id)
    assert result.status == "synced"
    assert gateway.created == [("SceneWeaver", None), ("adopted", "SceneWeaver")]
    assert gateway.added == [
        {
            "path": r"D:\image.png",
            "name": "image",
            "tags": result.tags,
            "annotation": result.annotation,
            "folder_id": "adopted",
        }
    ]
    assert "seed:42\nsmile\n-" in result.annotation
    sleep.assert_not_called()


def test_reuses_folders(setup_sync):
    service, asset, gateway, _ = setup_sync
    gateway.folders = [
        {"id": "p", "name": "SceneWeaver", "children": [{"id": "c", "name": "adopted"}]},
        {"id": "n", "name": "nanopost"},
    ]
    assert service.execute(asset.id).folder_id == "c"
    assert gateway.created == []


def test_sync_string_id(setup_sync, monkeypatch):
    service, asset, gateway, _ = setup_sync
    gateway.items = [{"annotation": "other"}] * 200

    def add_from_path(**payload):
        gateway.items.append({"id": "string-id", "annotation": payload["annotation"]})
        return "string-id"

    monkeypatch.setattr(gateway, "add_from_path", add_from_path)
    result = service.execute(asset.id)
    assert result.status == "synced"
    assert result.eagle_item_id == "string-id"


def test_sync_content_dedup_raises(setup_sync, monkeypatch):
    original_service, asset, gateway, uow = setup_sync
    service = SyncAssetToEagle(
        uow,
        gateway,
        original_service._asset_store,
        verify_attempts=3,
        verify_interval_seconds=0,
    )
    list_items = Mock(wraps=gateway.list_items)
    monkeypatch.setattr(gateway, "list_items", list_items)
    monkeypatch.setattr(gateway, "add_from_path", lambda **payload: "existing-content-id")
    with pytest.raises(EagleError) as error:
        service.execute(asset.id)
    assert error.value.code == EagleErrorCode.EAGLE_API_ERROR
    assert "existing-content-id" in str(error.value)
    assert "annotation" in str(error.value)
    assert "dedup" in str(error.value)
    assert list_items.call_count == 4  # One pre-add search and three verification searches.


def test_sync_retries_until_item_is_visible(setup_sync, monkeypatch):
    service, asset, gateway, _ = setup_sync
    post_add_calls = 0
    pre_add_calls = 0
    sleep = Mock()

    def list_items(*, limit=200, offset=0):
        nonlocal post_add_calls, pre_add_calls
        if not gateway.added:
            pre_add_calls += 1
            return []
        post_add_calls += 1
        return gateway.items[offset : offset + limit] if post_add_calls >= 3 else []

    monkeypatch.setattr(gateway, "list_items", list_items)
    monkeypatch.setattr("creator_studio.application.integrations.eagle_sync.time.sleep", sleep)
    result = service.execute(asset.id)
    assert result.status == "synced"
    assert result.eagle_item_id == "item"
    assert pre_add_calls == 1
    assert post_add_calls == 3
    assert len(gateway.added) == 1
    assert sleep.call_args_list == [call(1.0), call(1.0)]


@pytest.mark.parametrize("response", [None, 123, [], {}, {"id": None}, {"id": 123}, ""])
def test_sync_invalid_add_result(setup_sync, monkeypatch, response):
    service, asset, gateway, _ = setup_sync
    monkeypatch.setattr(gateway, "add_from_path", lambda **payload: response)
    with pytest.raises(EagleError) as error:
        service.execute(asset.id)
    assert error.value.code == EagleErrorCode.EAGLE_API_ERROR


def test_sync_uses_registered_item_id(setup_sync, monkeypatch):
    service, asset, gateway, _ = setup_sync

    def add_from_path(**payload):
        gateway.items.append({"id": "authoritative-id", "annotation": payload["annotation"]})
        return {"id": "returned-id"}

    monkeypatch.setattr(gateway, "add_from_path", add_from_path)
    assert service.execute(asset.id).eagle_item_id == "authoritative-id"


def test_idempotent_paginated(setup_sync):
    service, asset, gateway, _ = setup_sync
    gateway.items = [{"annotation": "other"}] * 200 + [
        {"id": "existing", "annotation": f"sw_asset:{asset.id}"}
    ]
    result = service.execute(asset.id)
    assert result.status == "already_synced"
    assert result.eagle_item_id == "existing"
    assert gateway.added == gateway.created == []


@pytest.mark.parametrize(
    "missing,code",
    [
        (True, EagleErrorCode.ASSET_NOT_FOUND),
        (False, EagleErrorCode.ASSET_NOT_ADOPTED),
    ],
)
def test_asset_errors(setup_sync, missing, code):
    service, asset, gateway, uow = setup_sync
    if missing:
        uow.assets.get = lambda asset_id: None
    else:
        asset.metadata.clear()
    with pytest.raises(EagleError) as error:
        service.execute(asset.id)
    assert error.value.code == code
    assert not gateway.added


def test_dry_run(setup_sync):
    service, asset, gateway, _ = setup_sync
    result = service.execute(asset.id, dry_run=True)
    assert result.status == "dry_run"
    assert result.folder_id is None
    assert result.windows_path == r"D:\image.png"
    assert gateway.created == gateway.added == []


def test_path_conversion():
    assert to_windows_path("/mnt/d/x/y.png") == r"D:\x\y.png"
    for path in (r"D:\x.png", r"\\server\share\x.png"):
        assert to_windows_path(path) == path
    runner = Mock(return_value=SimpleNamespace(returncode=1, stdout=""))
    with pytest.raises(EagleError) as error:
        to_windows_path("/unconvertible", wslpath_runner=runner)
    assert error.value.code == EagleErrorCode.EAGLE_PATH_UNCONVERTIBLE
    runner.return_value = SimpleNamespace(returncode=0, stdout="\\\\wsl.localhost\\Ubuntu\\x\n")
    assert to_windows_path("/x", wslpath_runner=runner) == r"\\wsl.localhost\Ubuntu\x"
