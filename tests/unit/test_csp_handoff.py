from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from creator_studio.application.assets.store_asset import StoreBytesCommand
from creator_studio.application.csp.handoff import HandoffError, PagePlan, PanelSlot
from creator_studio.domain.asset import AssetKind
from creator_studio.domain.ids import AssetId
from creator_studio.infrastructure.container import Container

_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
    b"\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _store_png(container: Container, label: bytes) -> str:
    stored = container.store_asset().execute(
        StoreBytesCommand(
            data=_PNG + label,
            kind=AssetKind.GENERATED,
            mime="image/png",
            relative_dir="generated",
            filename=f"{label.decode()}.png",
        )
    )
    return stored.id


def _pages(asset_id: str) -> list[PagePlan]:
    return [
        PagePlan(
            page_no=1,
            panels=[
                PanelSlot(
                    panel_no=1,
                    shot_id="shot_a",
                    script_event_ids=["evt1"],
                    asset_id=asset_id,
                )
            ],
        )
    ]


def _script() -> list[dict[str, str]]:
    return [{"id": "evt1", "kind": "speech", "speaker": "A", "text": "hello"}]


def test_adopted_asset_handoff_sha256_and_manifest(container: Container) -> None:
    asset_id = _store_png(container, b"adopt-ok")
    container.set_asset_decision().execute(asset_id, "adopted")

    with container.uow() as uow:
        asset = uow.assets.get(AssetId(asset_id))
        assert asset is not None
        adopted_sha = asset.sha256
        # snapshot provenance before handoff — must remain unchanged
        provenance_before = dict(asset.provenance)

    result = container.csp_handoff().build("proj_h5", _pages(asset_id), script_rows=_script())
    root = Path(result.path)
    panel = root / "pages" / "page_001" / "panel_01_clean.png"
    assert panel.exists()
    assert hashlib.sha256(panel.read_bytes()).hexdigest() == adopted_sha

    panel_meta = result.manifest["pages"][0]["panels"][0]
    assert panel_meta["asset_id"] == asset_id
    assert panel_meta["sha256"] == adopted_sha
    assert panel_meta["shot_id"] == "shot_a"
    assert panel_meta["panel_slot_id"] == "page_001_panel_01"
    assert panel_meta["script_event_ids"] == ["evt1"]
    assert result.revision == "r001"

    with container.uow() as uow:
        asset = uow.assets.get(AssetId(asset_id))
        assert asset is not None
        assert asset.sha256 == adopted_sha
        assert asset.provenance == provenance_before


def test_asset_missing_fails(container: Container) -> None:
    with pytest.raises(HandoffError, match="asset missing"):
        container.csp_handoff().build(
            "proj_h5",
            _pages("nonexistent_asset_id____________"),
            script_rows=_script(),
        )


def test_hash_mismatch_corrupted_asset_fails(container: Container, tmp_runtime: Path) -> None:
    asset_id = _store_png(container, b"corrupt")
    container.set_asset_decision().execute(asset_id, "adopted")

    with container.uow() as uow:
        asset = uow.assets.get(AssetId(asset_id))
        assert asset is not None
        path = container.asset_store.path_for_uri(asset.uri)
        path.write_bytes(_PNG + b"tampered-bytes")

    with pytest.raises(HandoffError, match="corrupted|hash mismatch"):
        container.csp_handoff().build("proj_h5", _pages(asset_id), script_rows=_script())
    # no published revision on failure
    assert not (tmp_runtime / "projects" / "proj_h5" / "csp_handoff" / "r001").exists()


def test_rejected_asset_cannot_handoff(container: Container) -> None:
    asset_id = _store_png(container, b"reject")
    container.set_asset_decision().execute(asset_id, "rejected")
    with pytest.raises(HandoffError, match="rejected"):
        container.csp_handoff().build("proj_h5", _pages(asset_id), script_rows=_script())


def test_pending_asset_cannot_handoff(container: Container) -> None:
    asset_id = _store_png(container, b"pending")
    with pytest.raises(HandoffError, match="not adopted"):
        container.csp_handoff().build("proj_h5", _pages(asset_id), script_rows=_script())


def test_same_revision_not_silently_overwritten(container: Container) -> None:
    asset_id = _store_png(container, b"revlock")
    container.set_asset_decision().execute(asset_id, "adopted")
    first = container.csp_handoff().build(
        "proj_h5",
        _pages(asset_id),
        script_rows=_script(),
        revision="r001",
    )
    assert first.revision == "r001"
    panel_before = Path(first.path) / "pages" / "page_001" / "panel_01_clean.png"
    before_bytes = panel_before.read_bytes()

    with pytest.raises(HandoffError, match="already exists"):
        container.csp_handoff().build(
            "proj_h5",
            _pages(asset_id),
            script_rows=_script(),
            revision="r001",
        )
    assert panel_before.read_bytes() == before_bytes

    second = container.csp_handoff().build(
        "proj_h5",
        _pages(asset_id),
        script_rows=_script(),
    )
    assert second.revision == "r002"
    assert Path(second.path).exists()
