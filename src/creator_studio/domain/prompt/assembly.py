from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class PromptComponent:
    component_id: str
    kind: str
    text: str
    component_version: str = "v1"
    subkind: str = ""
    content_rating: str = "general"
    precedence: int = 0
    priority: int = 0
    enabled: bool = True
    negative: bool = False
    model_scope: str = "anima"

    @property
    def ref(self) -> str:
        return f"{self.component_id}@{self.component_version}"


@dataclass(frozen=True)
class PromptAssemblyProfile:
    profile_id: str = "anima_story_panel"
    profile_version: str = "v1"
    content_rating: str = "general"
    model: str = "anima"
    # Order matches the Rize / Lize Helesta Anima base:
    # quality → 1girl → identity → style → traits → shot semantics…
    positive_order: tuple[str, ...] = (
        "quality",
        "subject_count",
        "character_identity",
        "style",
        "character_traits",
        "outfit",
        "expression",
        "pose",
        "gaze",
        "camera",
        "background",
        "lighting",
        "user_additions",
    )


@dataclass
class BuiltPrompt:
    positive: str
    negative: str
    components: list[PromptComponent]
    model_modifiers: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
