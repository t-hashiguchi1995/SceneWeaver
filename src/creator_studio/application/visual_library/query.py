from __future__ import annotations

from dataclasses import replace
from typing import Any

from creator_studio.application.visual_library.classify import classify_visual_kind
from creator_studio.application.visual_library.models import (
    VisualLibraryItem,
    make_ref,
)
from creator_studio.infrastructure.db.models.prompt import PromptPresetRow
from creator_studio.infrastructure.db.models.visual_library import VisualLibraryMetadataRow
from creator_studio.ports.unit_of_work import UnitOfWork


class VisualLibraryQuery:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def list_items(
        self,
        *,
        q: str = "",
        kind: str | None = None,
        content_rating: str | None = None,
        model: str | None = None,
        has_preview: bool | None = None,
    ) -> list[dict[str, Any]]:
        items = self._collect()
        return [
            item.to_summary_dict()
            for item in items
            if self._matches(
                item,
                q=q,
                kind=kind,
                content_rating=content_rating,
                model=model,
                has_preview=has_preview,
            )
        ]

    def get_item(self, source_type: str, source_id: str) -> dict[str, Any] | None:
        for item in self._collect():
            if item.source_type == source_type and item.source_id == source_id:
                return item.to_detail_dict()
        return None

    def _collect(self) -> list[VisualLibraryItem]:
        with self._uow as uow:
            meta_map = uow.visual_library_metadata.map_by_source()
            items: list[VisualLibraryItem] = []
            for preset in uow.prompt_presets.list_enabled():
                if preset.kind == "snippet" and not (preset.category or "").strip():
                    # Keep snippets but classify via category; empty stays other.
                    pass
                items.append(self._from_preset(preset, meta_map.get(("prompt_preset", preset.id))))
            for market in uow.marketplace.search(""):
                items.append(
                    self._from_marketplace(
                        market,
                        meta_map.get(("marketplace_item", market.id)),
                    )
                )
            items = self._merge_auto_tags(uow, items)
            items.sort(key=lambda item: (item.kind, (item.label_ja or item.label).lower(), item.ref))
            return items

    def _merge_auto_tags(
        self,
        uow: UnitOfWork,
        items: list[VisualLibraryItem],
    ) -> list[VisualLibraryItem]:
        """Append ImageTagger tags from thumbnail assets into display/search tags."""
        thumb_ids = [i.thumbnail_asset_id for i in items if i.thumbnail_asset_id]
        if not thumb_ids:
            return items
        auto_by_asset: dict[str, list[str]] = {}
        for row in uow.asset_tags.list_for_assets(thumb_ids):
            auto_by_asset.setdefault(row.asset_id, []).append(row.tag)
        if not auto_by_asset:
            return items
        merged: list[VisualLibraryItem] = []
        for item in items:
            auto = auto_by_asset.get(item.thumbnail_asset_id or "")
            if not auto:
                merged.append(item)
                continue
            seen: set[str] = set()
            tags: list[str] = []
            for tag in list(item.tags) + auto:
                key = tag.lower()
                if key in seen:
                    continue
                seen.add(key)
                tags.append(tag)
            merged.append(replace(item, tags=tags))
        return merged

    def _from_preset(
        self,
        preset: PromptPresetRow,
        meta: VisualLibraryMetadataRow | None,
    ) -> VisualLibraryItem:
        kind = (
            meta.visual_kind  # type: ignore[assignment]
            if meta and meta.visual_kind
            else classify_visual_kind(kind=preset.kind, category=preset.category)
        )
        tags = list(meta.tags_json) if meta and meta.tags_json else []
        model_scope = list(meta.model_scope_json) if meta and meta.model_scope_json else ["anima"]
        related = list(meta.related_refs_json) if meta and meta.related_refs_json else []
        return VisualLibraryItem(
            ref=make_ref("prompt_preset", preset.id),
            source_type="prompt_preset",
            source_id=preset.id,
            kind=kind,  # type: ignore[arg-type]
            label=preset.label,
            label_ja=meta.label_ja if meta else None,
            description=meta.description_ja if meta else None,
            thumbnail_asset_id=meta.thumbnail_asset_id if meta else None,
            preview_kind=meta.preview_kind if meta else None,  # type: ignore[arg-type]
            tags=[str(t) for t in tags],
            subcategory=meta.subcategory if meta else preset.category,
            content_rating=preset.content_rating,
            model_scope=[str(m) for m in model_scope],
            related_refs=[str(r) for r in related],
            prompt_fragment=preset.prompt_fragment,
            source=preset.source,
            source_file=preset.source_file,
        )

    def _from_marketplace(self, market: Any, meta: VisualLibraryMetadataRow | None) -> VisualLibraryItem:
        plate = str(market.canonical_plate_asset_id) if market.canonical_plate_asset_id else None
        thumb = (meta.thumbnail_asset_id if meta and meta.thumbnail_asset_id else None) or plate
        preview_kind = meta.preview_kind if meta and meta.preview_kind else (
            "imported_reference" if plate else None
        )
        tags = list(meta.tags_json) if meta and meta.tags_json else list(market.style_tags or [])
        model_scope = list(meta.model_scope_json) if meta and meta.model_scope_json else ["anima"]
        related = list(meta.related_refs_json) if meta and meta.related_refs_json else []
        kind = meta.visual_kind if meta and meta.visual_kind else "outfit"
        return VisualLibraryItem(
            ref=make_ref("marketplace_item", market.id),
            source_type="marketplace_item",
            source_id=market.id,
            kind=kind,  # type: ignore[arg-type]
            label=market.title,
            label_ja=meta.label_ja if meta else None,
            description=(meta.description_ja if meta and meta.description_ja else None)
            or (market.garment_description or None),
            thumbnail_asset_id=thumb,
            preview_kind=preview_kind,  # type: ignore[arg-type]
            tags=[str(t) for t in tags],
            subcategory=meta.subcategory if meta else market.category,
            content_rating="general",
            model_scope=[str(m) for m in model_scope],
            related_refs=[str(r) for r in related],
            prompt_fragment=None,
            source="marketplace",
            source_file=None,
        )

    def _matches(
        self,
        item: VisualLibraryItem,
        *,
        q: str,
        kind: str | None,
        content_rating: str | None,
        model: str | None,
        has_preview: bool | None,
    ) -> bool:
        if kind and item.kind != kind:
            return False
        if content_rating and item.content_rating != content_rating:
            return False
        if model and model not in item.model_scope and item.model_scope:
            return False
        if has_preview is True and not item.thumbnail_asset_id:
            return False
        if has_preview is False and item.thumbnail_asset_id:
            return False
        needle = q.strip().lower()
        if not needle:
            return True
        hay = " ".join(
            [
                item.label,
                item.label_ja or "",
                item.description or "",
                item.subcategory or "",
                " ".join(item.tags),
                item.kind,
            ]
        ).lower()
        return needle in hay
