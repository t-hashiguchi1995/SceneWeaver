from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from apps.api.deps import container
from creator_studio.application.image.quality_evaluation import average_hash, evaluate_image
from creator_studio.application.image.quality_evaluation_store import (
    known_image_hashes,
    load_evaluation,
    save_evaluation,
    save_review,
)
from creator_studio.domain.asset import AssetKind
from creator_studio.domain.ids import AssetId
from creator_studio.infrastructure.container import Container

router = APIRouter(prefix="/api/v1", tags=["quality-evaluations"])


class ReviewBody(BaseModel):
    reviewer_id: str = Field(min_length=1, pattern=r"\S")
    verdict: str = Field(min_length=1, pattern=r"\S")
    reasons: list[str] = Field(default_factory=list)


@router.post("/assets/{asset_id}/quality-evaluations")
def create_evaluation(asset_id: str, c: Container = Depends(container)) -> dict:
    with c.uow() as uow:
        asset = uow.assets.get(AssetId(asset_id))
        if asset is None:
            raise HTTPException(status_code=404, detail="asset not found")
        uri, is_original = asset.uri, asset.kind != AssetKind.DERIVED
    try:
        path = c.asset_store.path_for_uri(uri)
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=404, detail="asset content not found") from exc
    directory = c.settings.runtime_path() / "quality_evaluations"
    record = evaluate_image(
        path, is_original=is_original, known_hashes=known_image_hashes(directory=directory)
    )
    save_evaluation(
        record,
        directory=directory,
        image_hash=average_hash(path) if record.gate != "BLOCKED" else None,
    )
    return record.to_dict()


@router.get("/quality-evaluations/{evaluation_id}")
def get_evaluation(evaluation_id: str, c: Container = Depends(container)) -> dict:
    try:
        return load_evaluation(
            evaluation_id, directory=c.settings.runtime_path() / "quality_evaluations"
        ).to_dict()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="evaluation not found") from exc


@router.post("/quality-evaluations/{evaluation_id}/reviews")
def review_evaluation(
    evaluation_id: str, body: ReviewBody, c: Container = Depends(container)
) -> dict:
    try:
        return save_review(
            evaluation_id,
            body.reviewer_id,
            body.verdict,
            body.reasons,
            datetime.now(UTC).isoformat(),
            directory=c.settings.runtime_path() / "quality_evaluations",
        ).to_dict()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="evaluation not found") from exc
