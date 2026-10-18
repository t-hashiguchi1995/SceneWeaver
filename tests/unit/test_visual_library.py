from __future__ import annotations

from creator_studio.application.assets.store_asset import StoreBytesCommand
from creator_studio.application.e2e.visual_library_seed import seed_visual_library_catalog
from creator_studio.application.visual_library.classify import classify_visual_kind
from creator_studio.application.visual_library.models import make_ref
from creator_studio.application.visual_library.query import VisualLibraryQuery
from creator_studio.application.wardrobe.tryon import SeedMarketplaceItem
from creator_studio.domain.asset import AssetKind
from creator_studio.domain.ids import AssetId, new_id
from creator_studio.domain.timeutil import utc_now
from creator_studio.domain.wardrobe import MarketplaceItem
from creator_studio.infrastructure.db.models.prompt import PromptPresetRow
from creator_studio.infrastructure.db.models.visual_library import VisualLibraryMetadataRow


def test_classify_known_kinds_and_unknown_to_other():
    assert classify_visual_kind(kind="pose") == "pose"
    assert classify_visual_kind(kind="expression") == "expression"
    assert classify_visual_kind(kind="camera") == "camera"
    assert classify_visual_kind(kind="lighting") == "lighting"
    assert classify_visual_kind(kind="outfit") == "outfit"
    assert classify_visual_kind(kind="background") == "background"
    assert classify_visual_kind(kind="snippet", category="legacy_misc_xyz") == "other"
    assert classify_visual_kind(kind="snippet", category="location_cafe_sfw") == "other"
    assert classify_visual_kind(kind="category_label") == "other"


def test_make_ref_is_stable():
    assert make_ref("prompt_preset", "abc") == "prompt_preset:abc"
    assert make_ref("marketplace_item", "xyz") == "marketplace_item:xyz"


def test_prompt_preset_and_marketplace_map_to_visual_items(container):
    seed_visual_library_catalog(
        container.uow(),
        container.store_asset(),
        SeedMarketplaceItem(container.uow()),
    )
    query = VisualLibraryQuery(container.uow())
    items = query.list_items()
    refs = {item["ref"] for item in items}
    assert any(r.startswith("prompt_preset:") for r in refs)
    assert any(r.startswith("marketplace_item:") for r in refs)

    poses = query.list_items(kind="pose")
    assert len(poses) == 3
    assert all(p["kind"] == "pose" for p in poses)

    outfits = query.list_items(kind="outfit")
    assert len(outfits) == 2
    with_plate = next(o for o in outfits if o["label"] == "Soft Knit Cardigan")
    assert with_plate["thumbnail_asset_id"]
    assert with_plate["preview_kind"] == "imported_reference"
    assert with_plate["has_preview"] is True

    no_plate = next(o for o in outfits if o["label"] == "School Blazer")
    assert not no_plate["thumbnail_asset_id"]
    assert no_plate["has_preview"] is False

    found = query.list_items(q="振り向き")
    assert len(found) >= 1
    assert any("振り向き" in (i.get("label_ja") or "") for i in found)

    general = query.list_items(content_rating="general")
    assert len(general) == len(items)

    others = query.list_items(kind="other")
    assert any(i["label"] == "misc snippet" for i in others)

    with_preview = query.list_items(has_preview=True)
    without_preview = query.list_items(has_preview=False)
    assert with_preview
    assert without_preview
    assert all(i["has_preview"] for i in with_preview)
    assert all(not i["has_preview"] for i in without_preview)

    # Summary must not expose prompt_fragment
    for item in items:
        assert "prompt_fragment" not in item

    detail = query.get_item("prompt_preset", poses[0]["source_id"])
    assert detail is not None
    assert detail.get("prompt_fragment")


def test_source_type_source_id_unique_and_metadata_overrides(container):
    now = utc_now()
    preset_id = new_id()
    with container.uow() as uow:
        uow.prompt_presets.add_row(
            PromptPresetRow(
                id=preset_id,
                kind="snippet",
                label="mystery",
                prompt_fragment="mystery fragment",
                category="weird_legacy",
                content_rating="general",
                enabled=True,
                payload_json={},
                source="test",
                source_file="t.yaml",
                legacy_key="mystery",
                content_hash="h1",
                created_at=now,
                updated_at=now,
            )
        )
        uow.visual_library_metadata.add(
            VisualLibraryMetadataRow(
                id=new_id(),
                source_type="prompt_preset",
                source_id=preset_id,
                visual_kind="pose",
                label_ja="メタ補正ポーズ",
                description_ja="metadata override",
                thumbnail_asset_id=None,
                preview_kind=None,
                subcategory="pose",
                tags_json=["override"],
                model_scope_json=["anima"],
                related_refs_json=[],
                created_at=now,
                updated_at=now,
            )
        )
        uow.commit()

    item = VisualLibraryQuery(container.uow()).get_item("prompt_preset", preset_id)
    assert item is not None
    assert item["kind"] == "pose"
    assert item["label_ja"] == "メタ補正ポーズ"
    assert item["ref"] == f"prompt_preset:{preset_id}"

    with container.uow() as uow:
        mapped = uow.visual_library_metadata.map_by_source()
        assert ("prompt_preset", preset_id) in mapped
        assert len([k for k in mapped if k[0] == "prompt_preset" and k[1] == preset_id]) == 1


def test_canonical_plate_used_as_outfit_preview(container):
    plate = container.store_asset().execute(
        StoreBytesCommand(
            data=b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
            b"\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
            b"plate",
            kind=AssetKind.PLATE,
            mime="image/png",
            relative_dir="plates",
            filename="unit_plate.png",
        )
    )
    item = MarketplaceItem.create(
        title="Plate Dress",
        category="dress",
        region="full",
        garment_description="simple dress",
        canonical_plate_asset_id=AssetId(plate.id),
        style_tags=["dress"],
    )
    SeedMarketplaceItem(container.uow()).execute(item)
    mapped = VisualLibraryQuery(container.uow()).get_item("marketplace_item", item.id)
    assert mapped is not None
    assert mapped["thumbnail_asset_id"] == plate.id
    assert mapped["preview_kind"] == "imported_reference"
    assert mapped["kind"] == "outfit"
