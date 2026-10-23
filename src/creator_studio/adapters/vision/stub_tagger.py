"""Deterministic ImageTagger for CI / E2E (no ML deps)."""

from __future__ import annotations

import hashlib

from creator_studio.ports.image_tagger import ImageTag, TaggingResult


class StubImageTagger:
    SOURCE_MODEL = "stub"
    MODEL_VERSION = "1"

    def tag(self, image: bytes) -> TaggingResult:
        digest = hashlib.sha256(image).hexdigest()
        return TaggingResult(
            tags=[
                ImageTag(tag="stub_auto", category="meta", score=1.0),
                ImageTag(tag="1girl", category="general", score=0.95),
                ImageTag(tag=f"hash_{digest[:8]}", category="meta", score=0.5),
            ],
            source_model=self.SOURCE_MODEL,
            model_version=self.MODEL_VERSION,
        )
