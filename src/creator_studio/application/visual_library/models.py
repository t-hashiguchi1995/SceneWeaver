from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

SourceType = Literal["prompt_preset", "marketplace_item"]
VisualKind = Literal[
    "outfit",
    "pose",
    "expression",
    "camera",
    "lighting",
    "background",
    "other",
]
PreviewKind = Literal["curated", "generated", "imported_reference"]


@dataclass(frozen=True)
class VisualLibraryItem:
    ref: str
    source_type: SourceType
    source_id: str
    kind: VisualKind
    label: str
    content_rating: str
    tags: list[str] = field(default_factory=list)
    model_scope: list[str] = field(default_factory=list)
    related_refs: list[str] = field(default_factory=list)
    label_ja: str | None = None
    description: str | None = None
    thumbnail_asset_id: str | None = None
    preview_kind: PreviewKind | None = None
    subcategory: str | None = None
    prompt_fragment: str | None = None
    source: str | None = None
    source_file: str | None = None

    def to_summary_dict(self) -> dict:
        return {
            "ref": self.ref,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "kind": self.kind,
            "label": self.label,
            "label_ja": self.label_ja,
            "description": self.description,
            "thumbnail_asset_id": self.thumbnail_asset_id,
            "preview_kind": self.preview_kind,
            "tags": self.tags,
            "subcategory": self.subcategory,
            "content_rating": self.content_rating,
            "model_scope": self.model_scope,
            "related_refs": self.related_refs,
            "has_preview": bool(self.thumbnail_asset_id),
        }

    def to_detail_dict(self) -> dict:
        data = self.to_summary_dict()
        data.update(
            {
                "prompt_fragment": self.prompt_fragment,
                "source": self.source,
                "source_file": self.source_file,
            }
        )
        return data


def make_ref(source_type: str, source_id: str) -> str:
    return f"{source_type}:{source_id}"
