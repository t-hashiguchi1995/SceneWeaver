"""Saved, editable lettering layouts and derived PNG assets."""

from io import BytesIO
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, Field, model_validator

from apps.api.deps import container
from creator_studio.application.assets.store_asset import StoreBytesCommand
from creator_studio.application.lettering.models import LetteringLayer
from creator_studio.application.lettering.planner import plan_layout
from creator_studio.application.lettering.renderer import render_lettering
from creator_studio.application.lettering.store import load_layout, save_layout
from creator_studio.domain.asset import AssetKind
from creator_studio.domain.ids import AssetId
from creator_studio.infrastructure.container import Container

router = APIRouter(prefix="/api/v1/lettering/layouts", tags=["lettering"])


class LayerBody(BaseModel):
    kind: Literal["speech_bubble", "inner_voice", "narration", "sfx"] = "speech_bubble"
    block_id: str | None = None
    speaker_id: str | None = None
    text: str
    bbox_xyxy_norm: tuple[float, float, float, float] | None = None
    anchor_xy_norm: tuple[float, float] | None = None
    tail_mode: Literal["auto", "none"] = "auto"
    tail_tip_xy_norm: tuple[float, float] | None = None
    writing_mode: Literal["vertical-rl", "horizontal"] | None = None
    shape: Literal["oval", "cloud", "jagged", "rect", "none"] | None = None
    reading_order: int = 0
    font_profile: str | None = None
    min_font_px: int = Field(default=21, ge=1, le=512)

    @model_validator(mode="after")
    def validate_layer(self):
        LetteringLayer.from_dict({**self.model_dump(), "block_id": self.block_id or "block"})
        return self


class CreateBody(BaseModel):
    image_asset_id: str
    blocks: list[LayerBody]
    protected_regions: list[tuple[float, float, float, float]] = Field(default_factory=list)
    style_profile: str = "jp_manga_classic"

    @model_validator(mode="after")
    def validate_regions(self):
        for box in self.protected_regions:
            LetteringLayer("speech_bubble", "region", "", bbox_xyxy_norm=box)
        return self


class EditBody(BaseModel):
    layers: list[LayerBody]

    @model_validator(mode="after")
    def require_bounds(self):
        if any(v.bbox_xyxy_norm is None or not v.block_id for v in self.layers):
            raise ValueError("Edited layers require block_id and bbox_xyxy_norm")
        return self


def _directory(c):
    return c.settings.runtime_path() / "lettering_layouts"


def _load(layout_id, c):
    try:
        return load_layout(layout_id, directory=_directory(c))
    except FileNotFoundError as exc:
        raise HTTPException(404, "layout not found") from exc


def _image(asset_id, c):
    with c.uow() as uow:
        asset = uow.assets.get(AssetId(asset_id))
        if asset is None:
            raise HTTPException(404, "asset not found")
        uri = asset.uri
    try:
        path = c.asset_store.path_for_uri(uri)
        with Image.open(path) as image:
            return image.convert("RGB")
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(404, "asset content not found") from exc
    except (UnidentifiedImageError, OSError) as exc:
        raise HTTPException(400, "asset is not a readable image") from exc


@router.post("")
def create_layout(body: CreateBody, c: Annotated[Container, Depends(container)]):
    image = _image(body.image_asset_id, c)
    blocks = []
    for i, block in enumerate(body.blocks):
        data = block.model_dump()
        data["block_id"] = data["block_id"] or f"block_{i + 1}"
        blocks.append(data)
    try:
        layout = plan_layout(
            image_w=image.width,
            image_h=image.height,
            blocks=blocks,
            protected_regions_norm=body.protected_regions,
        )
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    layout.image_asset_id = body.image_asset_id
    layout.style_profile = body.style_profile
    save_layout(layout, directory=_directory(c))
    return layout.to_dict()


@router.get("/{layout_id}")
def get_layout(layout_id: str, c: Annotated[Container, Depends(container)]):
    return _load(layout_id, c).to_dict()


@router.put("/{layout_id}")
def edit_layout(layout_id: str, body: EditBody, c: Annotated[Container, Depends(container)]):
    layout = _load(layout_id, c)
    layout.layers = [LetteringLayer.from_dict(v.model_dump()) for v in body.layers]
    layout.revision += 1
    save_layout(layout, directory=_directory(c))
    return layout.to_dict()


@router.post("/{layout_id}/render")
def render_layout(layout_id: str, c: Annotated[Container, Depends(container)]):
    layout = _load(layout_id, c)
    image = _image(layout.image_asset_id, c)
    try:
        rendered = render_lettering(image, layout)
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    save_layout(layout, directory=_directory(c))
    output = BytesIO()
    rendered.save(output, format="PNG")
    asset = c.store_asset().execute(
        StoreBytesCommand(
            data=output.getvalue(),
            kind=AssetKind.DERIVED,
            mime="image/png",
            relative_dir="derived",
            filename="lettering.png",
            deduplicate=False,
            provenance={
                "source_asset_id": layout.image_asset_id,
                "operation": "lettering",
                "layout_id": layout.layout_id,
                "revision": layout.revision,
            },
        )
    )
    return {**asset.__dict__, "warnings": layout.warnings}


class ProtectedRegionBody(BaseModel):
    id: str | None = None
    role: str = "protected"
    bbox_xyxy_norm: tuple[float, float, float, float]

    @model_validator(mode="after")
    def validate_bounds(self):
        LetteringLayer("speech_bubble", "region", "", bbox_xyxy_norm=self.bbox_xyxy_norm)
        return self


class EvaluateBody(BaseModel):
    protected_regions: list[ProtectedRegionBody] = Field(default_factory=list)


@router.post("/{layout_id}/evaluate")
def evaluate(
    layout_id: str, c: Annotated[Container, Depends(container)], body: EvaluateBody | None = None
):
    from creator_studio.application.lettering.quality import evaluate_layout
    from creator_studio.application.lettering.quality_store import save_evaluation

    layout = _load(layout_id, c)
    result = evaluate_layout(
        layout,
        layout.canvas["width"],
        layout.canvas["height"],
        [v.model_dump() for v in body.protected_regions] if body else [],
    )
    save_evaluation(result, directory=c.settings.runtime_path() / "lettering_quality")
    return result


quality_router = APIRouter(prefix="/api/v1/lettering/quality", tags=["lettering"])


@quality_router.get("/{evaluation_id}")
def get_quality(evaluation_id: str, c: Annotated[Container, Depends(container)]):
    from creator_studio.application.lettering.quality_store import load_evaluation

    try:
        return load_evaluation(
            evaluation_id, directory=c.settings.runtime_path() / "lettering_quality"
        )
    except FileNotFoundError as exc:
        raise HTTPException(404, "quality evaluation not found") from exc
