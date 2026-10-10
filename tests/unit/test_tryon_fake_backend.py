from __future__ import annotations

import pytest

from creator_studio.application.assets.store_asset import StoreBytesCommand
from creator_studio.application.projects.create_project import CreateProjectCommand
from creator_studio.domain.asset import AssetKind
from creator_studio.domain.ids import AssetId, SceneId
from creator_studio.domain.wardrobe import MarketplaceItem
from creator_studio.infrastructure.container import Container

_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
    b"\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)


def test_tryon_requires_source_and_preserves_base(container: Container) -> None:
    char = container.create_character().execute("A")
    plate = container.store_asset().execute(
        StoreBytesCommand(
            data=_PNG + b"plate",
            kind=AssetKind.PLATE,
            mime="image/png",
            relative_dir="plates",
            filename="cardigan.png",
        )
    )
    item = MarketplaceItem.create(
        title="Soft Cardigan",
        category="outerwear",
        region="tops",
        garment_description="cream knit cardigan",
        canonical_plate_asset_id=AssetId(plate.id),
    )
    container.seed_marketplace_item().execute(item)

    with pytest.raises(ValueError, match="tryon_base_asset_id"):
        container.run_tryon().execute(character_id=char.id, marketplace_item_id=item.id)

    base = container.store_asset().execute(
        StoreBytesCommand(
            data=_PNG + b"base",
            kind=AssetKind.REFERENCE,
            mime="image/png",
            relative_dir="characters",
            filename="fullbody.png",
        )
    )
    container.update_visual_identity().execute(
        char.id, {"tryon_base_asset_id": base.id, "hair": "black"}
    )

    found = container.search_market().execute("cardigan")
    assert any(i["id"] == item.id for i in found)

    result = container.run_tryon().execute(character_id=char.id, marketplace_item_id=item.id)
    assert result.status == "succeeded"
    assert len(result.candidate_asset_ids) == 4

    with container.uow() as uow:
        source = uow.assets.get(AssetId(base.id))
        assert source is not None
        assert source.sha256 == base.sha256

    project = container.create_project().execute(CreateProjectCommand(title="P"))
    scene = container.create_scene().execute(project.id, "S1")
    adopted = container.adopt_tryon().execute(
        result.session_id,
        result.candidate_asset_ids[0],
        scene_id=scene.id,
    )
    assert adopted["adopted_asset_id"] == result.candidate_asset_ids[0]
    assert adopted["references"]
    with container.uow() as uow:
        scene2 = uow.scenes.get(SceneId(scene.id))
        assert scene2 is not None
        assert scene2.initial_state["outfit_profile_id"] == adopted["outfit_profile_id"]