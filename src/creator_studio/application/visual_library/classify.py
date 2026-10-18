"""Map PromptPreset kind/category onto Visual Library kinds.

Unknown values become ``other`` — never invent pose/camera from free text.
Metadata can override later.
"""

from __future__ import annotations

from creator_studio.application.visual_library.models import VisualKind


_KIND_MAP: dict[str, VisualKind] = {
    "pose": "pose",
    "expression": "expression",
    "camera": "camera",
    "lighting": "lighting",
    "outfit": "outfit",
    "costume": "outfit",
    "background": "background",
    "location": "background",
}

# Exact category matches only — no prefix guessing.
_CATEGORY_EXACT: dict[str, VisualKind] = {
    "pose": "pose",
    "expression": "expression",
    "camera": "camera",
    "lighting": "lighting",
    "outfit": "outfit",
    "costume": "outfit",
    "background": "background",
    "location": "background",
}


def classify_visual_kind(*, kind: str | None, category: str | None = None) -> VisualKind:
    key = (kind or "").strip().lower()
    if key in _KIND_MAP:
        return _KIND_MAP[key]
    cat = (category or "").strip().lower()
    if cat in _CATEGORY_EXACT:
        return _CATEGORY_EXACT[cat]
    return "other"
