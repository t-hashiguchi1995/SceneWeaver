"""OutfitProfile must belong to the selected Character before prompt/render."""

from __future__ import annotations

import pytest

from creator_studio.application.assets.store_asset import StoreBytesCommand
from creator_studio.application.projects.create_project import CreateProjectCommand
from creator_studio.application.prompt.context import resolve_prompt_context
from creator_studio.domain.asset import AssetKind
from creator_studio.domain.ids import AssetId, CharacterId
from creator_studio.domain.wardrobe import MarketplaceItem, OutfitProfile
from creator_studio.infrastructure.container import Container

_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
    b"\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _seed_character_with_base(container: Container, name: str) -> str:
    char = container.create_character().execute(name)
    base = container.store_asset().execute(
        StoreBytesCommand(
            data=_PNG + name.encode(),
            kind=AssetKind.REFERENCE,
            mime="image/png",
            relative_dir="characters",
            filename=f"{name}.png",
        )
    )
    container.update_visual_identity().execute(
        char.id,
        {
            "tryon_base_asset_id": base.id,
            "identity_tags": [f"char_{name}"],
            "hair": f"{name}_hair",
        },
    )
    return char.id


def test_resolve_prompt_context_rejects_foreign_outfit(container: Container) -> None:
    char_a = _seed_character_with_base(container, "Rize")
    char_b = _seed_character_with_base(container, "Ange")
    foreign = OutfitProfile.create(
        "Ange Dress",
        character_id=CharacterId(char_b),
        semantic={"garment_description": "red dress"},
    )
    with container.uow() as uow:
        uow.outfit_profiles.add(foreign)
        uow.commit()

    project = container.create_project().execute(CreateProjectCommand(title="Own"))
    scene = container.create_scene().execute(project.id, "Cafe")
    beat = container.create_beat().execute(scene_id=scene.id, intent="greet", speaker_id=char_a)
    shot = container.shot_pipeline().plan_shot(beat.id)
    container.shot_pipeline().update_shot(shot.id, {"outfit_profile_id": foreign.id})

    with container.uow() as uow:
        from creator_studio.domain.ids import ShotId

        reloaded = uow.shots.get(ShotId(shot.id))
        assert reloaded is not None
        with pytest.raises(ValueError, match="outfit does not belong to selected character"):
            resolve_prompt_context(uow, reloaded)


def test_resolve_prompt_context_accepts_owned_outfit(container: Container) -> None:
    char_a = _seed_character_with_base(container, "Rory")
    owned = OutfitProfile.create(
        "Rory Cardigan",
        character_id=CharacterId(char_a),
        semantic={"garment_description": "cream cardigan"},
    )
    with container.uow() as uow:
        uow.outfit_profiles.add(owned)
        uow.commit()

    project = container.create_project().execute(CreateProjectCommand(title="OwnOK"))
    scene = container.create_scene().execute(project.id, "Cafe")
    beat = container.create_beat().execute(scene_id=scene.id, intent="greet", speaker_id=char_a)
    shot = container.shot_pipeline().plan_shot(beat.id)
    container.shot_pipeline().update_shot(shot.id, {"outfit_profile_id": owned.id})

    with container.uow() as uow:
        from creator_studio.domain.ids import ShotId

        reloaded = uow.shots.get(ShotId(shot.id))
        assert reloaded is not None
        spec = resolve_prompt_context(uow, reloaded)
        assert "cream cardigan" in str(spec.get("outfit_tags"))
        assert spec.get("outfit_profile_id") == owned.id
        assert spec.get("_outfit_character_id") == char_a


def test_tryon_adopt_outfit_stays_on_owner_character(container: Container) -> None:
    """Adopted OutfitProfile is owned by the Try-On character (fixture for multi-outfit)."""
    char = _seed_character_with_base(container, "Rory")
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
    result = container.run_tryon().execute(character_id=char, marketplace_item_id=item.id)
    adopted = container.adopt_tryon().execute(result.session_id, result.candidate_asset_ids[0])
    with container.uow() as uow:
        profile = uow.outfit_profiles.get(adopted["outfit_profile_id"])
        assert profile is not None
        assert str(profile.character_id) == char
