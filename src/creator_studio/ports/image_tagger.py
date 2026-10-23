"""Image tagging Port — Domain/Application never import torch/transformers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class ImageTag:
    tag: str
    category: str
    score: float


@dataclass(frozen=True)
class TaggingResult:
    tags: list[ImageTag] = field(default_factory=list)
    source_model: str = ""
    model_version: str = ""


class ImageTagger(Protocol):
    def tag(self, image: bytes) -> TaggingResult:
        """Return tags for raw image bytes. Must not mutate caller state."""
        ...
