"""PixAI Tagger adapter — torch / transformers / trust_remote_code stay here only.

Optional: ``pip install 'sceneweaver[vision]'``.
Official path: ``transformers.pipeline(..., trust_remote_code=True)`` with a pinned
revision (never floating ``main``).
"""

from __future__ import annotations

import io
import logging
from typing import Any

from creator_studio.ports.image_tagger import ImageTag, TaggingResult

logger = logging.getLogger("sceneweaver.vision.pixai")

DEFAULT_MODEL_ID = "pixai-labs/pixai-tagger-v1.0"
# Pin remote code + weights. Update deliberately when bumping the tagger.
PINNED_REVISION = "9fe10addf9326e292da8a85a98ea74cd91b41771"


class PixAITaggerAdapter:
    """Lazy-loads Hugging Face PixAI tagger via transformers.pipeline."""

    def __init__(
        self,
        *,
        model_id: str = DEFAULT_MODEL_ID,
        revision: str = PINNED_REVISION,
        threshold: float | dict[str, float] | None = None,
    ) -> None:
        self._model_id = model_id
        self._revision = revision
        self._threshold = threshold
        self._pipeline: Any = None

    @property
    def model_version(self) -> str:
        """Provenance version == pinned HF revision."""
        return self._revision

    def tag(self, image: bytes) -> TaggingResult:
        pipe = self._ensure_loaded()
        from PIL import Image  # type: ignore[import-untyped]

        pil = Image.open(io.BytesIO(image)).convert("RGB")
        kwargs: dict[str, Any] = {}
        if self._threshold is not None:
            kwargs["threshold"] = self._threshold
        raw = pipe(pil, **kwargs)["results"]
        tags = self._flatten_results(raw)
        return TaggingResult(
            tags=tags,
            source_model=self._model_id,
            model_version=self._revision,
        )

    def _ensure_loaded(self) -> Any:
        if self._pipeline is not None:
            return self._pipeline
        try:
            from transformers import pipeline
        except ImportError as exc:
            raise RuntimeError(
                "PixAITaggerAdapter requires optional deps: "
                "pip install 'sceneweaver[vision]' "
                "(torch, torchvision, transformers, timm, numpy, Pillow)"
            ) from exc

        logger.info(
            "loading PixAI tagger model_id=%s revision=%s",
            self._model_id,
            self._revision,
        )
        self._pipeline = pipeline(
            model=self._model_id,
            image_processor=self._model_id,
            trust_remote_code=True,
            revision=self._revision,
        )
        return self._pipeline

    @staticmethod
    def _flatten_results(raw: Any) -> list[ImageTag]:
        """Pipeline returns {category: {tag: score, ...}, ...}."""
        if not isinstance(raw, dict):
            return []
        results: list[ImageTag] = []
        for category, labels in raw.items():
            if not isinstance(labels, dict):
                continue
            cat = str(category)
            for tag, score in labels.items():
                try:
                    value = float(score)
                except (TypeError, ValueError):
                    continue
                name = str(tag).strip()
                if not name:
                    continue
                results.append(ImageTag(tag=name, category=cat, score=value))
        results.sort(key=lambda t: t.score, reverse=True)
        return results
