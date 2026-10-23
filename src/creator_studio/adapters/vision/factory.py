"""Build ImageTagger instances from an explicit snapshot (not live settings)."""

from __future__ import annotations

from creator_studio.adapters.vision.stub_tagger import StubImageTagger
from creator_studio.ports.image_tagger import ImageTagger


def build_image_tagger(
    *,
    image_tagger: str,
    model_id: str | None = None,
    model_version: str | None = None,
    threshold: float | None = None,
) -> ImageTagger:
    """Construct a tagger from enqueue-time snapshot fields.

    Used by the worker so queued TAG_ASSET jobs survive later settings changes
    (e.g. stub enqueue → IMAGE_TAGGER=off → still runs stub).
    """
    backend = image_tagger.strip().lower()
    if backend in {"", "off", "none"}:
        raise RuntimeError(
            f"cannot build ImageTagger for disabled backend={image_tagger!r}"
        )
    if backend == "stub":
        return StubImageTagger()
    if backend == "pixai":
        from creator_studio.adapters.vision.pixai_tagger import (
            DEFAULT_MODEL_ID,
            PINNED_REVISION,
            PixAITaggerAdapter,
        )

        return PixAITaggerAdapter(
            model_id=(model_id or DEFAULT_MODEL_ID).strip(),
            revision=(model_version or PINNED_REVISION).strip(),
            threshold=threshold,
        )
    raise RuntimeError(f"unknown image_tagger={image_tagger!r}; use stub|pixai")
