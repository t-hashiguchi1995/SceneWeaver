"""Live PixAI tagger — runs only when SCENEWEAVER_IMAGE_TAGGER=pixai.

When that env is set, missing vision deps or load failure must FAIL (not skip),
so Adapter / dependency regressions are not hidden.
"""

from __future__ import annotations

import os

import pytest

from creator_studio.adapters.vision.pixai_tagger import PINNED_REVISION, PixAITaggerAdapter


pytestmark = pytest.mark.skipif(
    os.environ.get("SCENEWEAVER_IMAGE_TAGGER", "off").lower() != "pixai",
    reason="Set SCENEWEAVER_IMAGE_TAGGER=pixai (and install sceneweaver[vision]) for live PixAI",
)


def test_pixai_tagger_tags_sample_png() -> None:
    # Minimal 1x1 PNG
    png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
        b"\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    # Do not catch ImportError / RuntimeError — pixai mode must surface load failures.
    result = PixAITaggerAdapter(revision=PINNED_REVISION).tag(png)
    assert result.source_model == "pixai-labs/pixai-tagger-v1.0"
    assert result.model_version == PINNED_REVISION
    assert isinstance(result.tags, list)
