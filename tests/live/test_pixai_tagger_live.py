"""Live PixAI tagger — skipped unless SCENEWEAVER_IMAGE_TAGGER=pixai and vision extra installed.

CI/E2E must use StubImageTagger. This module is opt-in only.
"""

from __future__ import annotations

import os

import pytest

from creator_studio.adapters.vision.pixai_tagger import PixAITaggerAdapter


pytestmark = pytest.mark.skipif(
    os.environ.get("SCENEWEAVER_IMAGE_TAGGER", "stub").lower() != "pixai",
    reason="Set SCENEWEAVER_IMAGE_TAGGER=pixai and install sceneweaver[vision] for live PixAI",
)


def test_pixai_tagger_tags_sample_png() -> None:
    # Minimal 1x1 PNG
    png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
        b"\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    try:
        result = PixAITaggerAdapter(threshold=0.2).tag(png)
    except RuntimeError as exc:
        if "optional deps" in str(exc):
            pytest.skip(str(exc))
        raise
    assert result.source_model
    assert isinstance(result.tags, list)
