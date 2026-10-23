"""Tag an asset via ImageTagger and persist asset_tags.

Tagging failures must never roll back Asset creation — callers enqueue this as a
separate job and treat job failure as non-fatal to generation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from creator_studio.domain.asset_tag import AssetTag
from creator_studio.domain.ids import AssetId
from creator_studio.domain.job import Job, JobKind
from creator_studio.ports.asset_store import AssetStore
from creator_studio.ports.image_tagger import ImageTagger, TaggingResult
from creator_studio.ports.unit_of_work import UnitOfWork

logger = logging.getLogger("sceneweaver.assets.tag")


@dataclass
class AssetTagDTO:
    id: str
    asset_id: str
    tag: str
    category: str
    score: float
    source_model: str
    model_version: str
    created_at: str


def tag_to_dto(tag: AssetTag) -> AssetTagDTO:
    return AssetTagDTO(
        id=tag.id,
        asset_id=tag.asset_id,
        tag=tag.tag,
        category=tag.category,
        score=tag.score,
        source_model=tag.source_model,
        model_version=tag.model_version,
        created_at=tag.created_at.isoformat(),
    )


def tagging_idempotency_key(asset_id: str) -> str:
    return f"tag-asset:{asset_id}"


def schedule_asset_tagging(uow: UnitOfWork, asset_id: str) -> None:
    """Enqueue TAG_ASSET inside the caller's transaction. Never raises."""
    try:
        key = tagging_idempotency_key(asset_id)
        existing = uow.jobs.get_by_idempotency_key(key)
        if existing is not None:
            return
        job = Job.create(
            JobKind.TAG_ASSET,
            {"asset_id": asset_id},
            idempotency_key=key,
            max_attempts=2,
        )
        uow.jobs.add(job)
    except Exception as exc:  # noqa: BLE001 — tagging must not fail asset save
        logger.warning("failed to schedule asset tagging asset_id=%s: %s", asset_id, exc)


class TagAsset:
    def __init__(
        self,
        uow: UnitOfWork,
        store: AssetStore,
        tagger: ImageTagger,
    ) -> None:
        self._uow = uow
        self._store = store
        self._tagger = tagger

    def execute(self, asset_id: str) -> list[AssetTagDTO]:
        with self._uow as uow:
            asset = uow.assets.get(AssetId(asset_id))
            if asset is None:
                raise ValueError(f"asset not found: {asset_id}")
            path = self._store.path_for_uri(asset.uri)
            image = path.read_bytes()

        result = self._tagger.tag(image)
        tags = self._persist(asset_id, result)
        return [tag_to_dto(t) for t in tags]

    def list_tags(self, asset_id: str) -> list[AssetTagDTO]:
        with self._uow as uow:
            return [tag_to_dto(t) for t in uow.asset_tags.list_for_asset(asset_id)]

    def _persist(self, asset_id: str, result: TaggingResult) -> list[AssetTag]:
        entities = [
            AssetTag.create(
                asset_id=asset_id,
                tag=item.tag,
                category=item.category or "general",
                score=float(item.score),
                source_model=result.source_model,
                model_version=result.model_version,
            )
            for item in result.tags
            if item.tag.strip()
        ]
        with self._uow as uow:
            saved = uow.asset_tags.upsert_many(entities)
            uow.commit()
            return uow.asset_tags.list_for_asset(asset_id) if saved else []


class ListAssetTags:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, asset_id: str) -> list[dict[str, Any]]:
        with self._uow as uow:
            return [tag_to_dto(t).__dict__ for t in uow.asset_tags.list_for_asset(asset_id)]
