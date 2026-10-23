from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from creator_studio.application.assets.tag_asset import schedule_asset_tagging
from creator_studio.application.image.runner import candidate_count_for_backend, submit_wait_collect
from creator_studio.domain.asset import Asset, AssetKind
from creator_studio.domain.ids import AssetId, CharacterId, SceneId
from creator_studio.domain.wardrobe import MarketplaceItem, OutfitProfile, TryOnSession
from creator_studio.infrastructure.prompts import PromptRegistry
from creator_studio.ports.asset_store import AssetStore
from creator_studio.ports.image_backend import ImageBackend, RenderPlanDTO
from creator_studio.ports.unit_of_work import UnitOfWork


@dataclass
class TryOnResultDTO:
    session_id: str
    candidate_asset_ids: list[str]
    status: str


class SearchMarket:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, query: str = "", category: str | None = None) -> list[dict[str, Any]]:
        with self._uow as uow:
            items = uow.marketplace.search(query, category=category)
            return [
                {
                    "id": i.id,
                    "title": i.title,
                    "category": i.category,
                    "region": i.region,
                    "garment_description": i.garment_description,
                    "canonical_plate_asset_id": str(i.canonical_plate_asset_id)
                    if i.canonical_plate_asset_id
                    else None,
                    "style_tags": i.style_tags,
                    "colors": i.colors,
                }
                for i in items
            ]


class SeedMarketplaceItem:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, item: MarketplaceItem) -> MarketplaceItem:
        with self._uow as uow:
            uow.marketplace.add(item)
            uow.commit()
            return item


class RunTryOn:
    def __init__(
        self,
        uow: UnitOfWork,
        image: ImageBackend,
        store: AssetStore,
        prompts: PromptRegistry | None = None,
    ) -> None:
        self._uow = uow
        self._image = image
        self._store = store
        self._prompts = prompts or PromptRegistry()

    def execute(
        self,
        *,
        character_id: str,
        marketplace_item_id: str,
        source_asset_id: str | None = None,
        scene_id: str | None = None,
    ) -> TryOnResultDTO:
        with self._uow as uow:
            character = uow.characters.get(CharacterId(character_id))
            item = uow.marketplace.get(marketplace_item_id)
            if character is None or item is None:
                raise ValueError("character or marketplace item not found")
            if item.canonical_plate_asset_id is None:
                raise ValueError("marketplace item missing canonical plate")

            source_id = source_asset_id
            if not source_id and character.visual_identity.tryon_base_asset_id:
                source_id = str(character.visual_identity.tryon_base_asset_id)
            if not source_id:
                raise ValueError(
                    "Try-On requires tryon_base_asset_id or explicit source_asset_id"
                )
            source_asset = uow.assets.get(AssetId(source_id))
            plate_asset = uow.assets.get(item.canonical_plate_asset_id)
            if source_asset is None or plate_asset is None:
                raise ValueError("source or plate asset missing")

            profile = OutfitProfile.create(
                title=item.title,
                character_id=character.id,
                marketplace_item_id=item.id,
                semantic={"garment_description": item.garment_description, "region": item.region},
            )
            uow.outfit_profiles.add(profile)

            session = TryOnSession.create(
                character_id=character.id,
                outfit_profile_id=profile.id,
                source_asset_id=AssetId(source_id),
                plate_asset_id=item.canonical_plate_asset_id,
            )
            if scene_id:
                scene = uow.scenes.get(SceneId(scene_id))
                if scene is None:
                    raise ValueError("scene not found")
                scene.initial_state = {**scene.initial_state, "tryon_session_ids": [
                    *scene.initial_state.get("tryon_session_ids", []), session.id]}
                uow.scenes.save(scene)
            uow.tryon_sessions.add(session)

            prompt = self._prompts.render(
                "wardrobe/tryon_full_v1.jinja2",
                outfit_description=item.garment_description,
                footwear_instruction="Keep existing footwear unless outfit includes shoes.",
            )
            plan = RenderPlanDTO(
                capability="OutfitTryOn",
                template_id="qwen_tryon_v1",
                seed=42,
                slots={
                    "edit_prompt": prompt,
                    "candidate_count": candidate_count_for_backend(self._image),
                    "character_image": source_asset.uri,
                    "garment_image": plate_asset.uri,
                },
                refs={"source": source_asset.uri, "plate": plate_asset.uri},
            )
            validation = self._image.validate(plan)
            if not validation.ok:
                session.status = "failed"
                uow.tryon_sessions.save(session)
                uow.commit()
                raise ValueError("; ".join(validation.errors))

            try:
                ref, artifacts = submit_wait_collect(self._image, plan)
            except Exception:
                session.status = "blocked"
                uow.tryon_sessions.save(session)
                uow.commit()
                raise

            candidates: list[str] = []
            for artifact in artifacts:
                blob = self._store.put_bytes(
                    artifact.bytes_data,
                    relative_dir="derived/tryon",
                    filename="tryon.png",
                )
                meta = artifact.metadata or {}
                provenance = {
                    "capability": "OutfitTryOn",
                    "provider": meta.get("provider") or ref.provider,
                    "workflow_template_id": meta.get("workflow_template_id") or plan.template_id,
                    "template_id": plan.template_id,
                    "workflow_hash": meta.get("workflow_hash") or "",
                    "model_id": meta.get("model_id"),
                    "seed": meta.get("seed", plan.seed),
                    "external_job_ref": meta.get("external_job_ref") or ref.ref,
                    "source_asset_id": source_id,
                    "plate_asset_id": str(item.canonical_plate_asset_id),
                    "prompt_version": "tryon_full_v1",
                }
                existing = uow.assets.find_by_sha256(blob.sha256)
                if existing:
                    candidates.append(str(existing.id))
                    continue
                asset = Asset.create(
                    sha256=blob.sha256,
                    uri=blob.uri,
                    kind=AssetKind.DERIVED,
                    mime=artifact.mime,
                    byte_size=blob.byte_size,
                    provenance=provenance,
                )
                uow.assets.add(asset)
                schedule_asset_tagging(uow, str(asset.id))
                candidates.append(str(asset.id))

            session.candidate_asset_ids = candidates
            session.status = "succeeded"
            uow.tryon_sessions.save(session)
            uow.commit()
            return TryOnResultDTO(
                session_id=session.id,
                candidate_asset_ids=candidates,
                status=session.status,
            )


class AdoptTryOn:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(
        self,
        session_id: str,
        asset_id: str,
        *,
        scene_id: str | None = None,
    ) -> dict[str, Any]:
        with self._uow as uow:
            session = uow.tryon_sessions.get(session_id)
            if session is None:
                raise ValueError("tryon session not found")
            if asset_id not in session.candidate_asset_ids:
                raise ValueError("asset not in session candidates")
            if uow.assets.get(session.source_asset_id) is None:
                raise ValueError("source asset missing")

            profile = uow.outfit_profiles.get(session.outfit_profile_id)
            if profile is None:
                raise ValueError("outfit profile missing")
            profile.add_verified_reference(AssetId(asset_id))
            uow.outfit_profiles.save(profile)

            session.adopted_asset_id = AssetId(asset_id)
            session.status = "adopted"
            uow.tryon_sessions.save(session)

            if scene_id:
                scene = uow.scenes.get(SceneId(scene_id))
                if scene is None:
                    raise ValueError("scene not found")
                scene.initial_state = {
                    **scene.initial_state,
                    "outfit_profile_id": profile.id,
                }
                uow.scenes.save(scene)

            uow.commit()
            return {
                "session_id": session.id,
                "outfit_profile_id": profile.id,
                "adopted_asset_id": asset_id,
                "references": profile.references,
                "source_asset_id": str(session.source_asset_id),
            }