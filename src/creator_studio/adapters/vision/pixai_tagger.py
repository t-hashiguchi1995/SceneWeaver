"""PixAI Tagger adapter — torch / transformers / trust_remote_code stay here only.

Optional dependency group: ``pip install 'sceneweaver[vision]'``.
Default CI/E2E uses StubImageTagger; this adapter is for live-test / local opt-in.
"""

from __future__ import annotations

import io
import logging
from typing import Any

from creator_studio.ports.image_tagger import ImageTag, TaggingResult

logger = logging.getLogger("sceneweaver.vision.pixai")

DEFAULT_MODEL_ID = "pixai-labs/pixai-tagger-v1.0"
DEFAULT_MODEL_VERSION = "1.0"


class PixAITaggerAdapter:
    """Lazy-loads Hugging Face PixAI tagger. Never import this from Domain/Application."""

    def __init__(
        self,
        *,
        model_id: str = DEFAULT_MODEL_ID,
        model_version: str = DEFAULT_MODEL_VERSION,
        threshold: float = 0.3,
        device: str | None = None,
    ) -> None:
        self._model_id = model_id
        self._model_version = model_version
        self._threshold = threshold
        self._device = device
        self._model: Any = None
        self._processor: Any = None

    def tag(self, image: bytes) -> TaggingResult:
        model, processor = self._ensure_loaded()
        from PIL import Image  # type: ignore[import-untyped]

        pil = Image.open(io.BytesIO(image)).convert("RGB")
        inputs = processor(images=pil, return_tensors="pt")
        if self._device:
            inputs = {k: v.to(self._device) for k, v in inputs.items()}
            model = model.to(self._device)

        import torch  # type: ignore[import-untyped]

        with torch.no_grad():
            outputs = model(**inputs)

        tags = self._decode_tags(outputs, processor)
        return TaggingResult(
            tags=tags,
            source_model=self._model_id,
            model_version=self._model_version,
        )

    def _ensure_loaded(self) -> tuple[Any, Any]:
        if self._model is not None and self._processor is not None:
            return self._model, self._processor
        try:
            from transformers import AutoImageProcessor, AutoModelForImageClassification
        except ImportError as exc:  # pragma: no cover - exercised only when vision extra missing
            raise RuntimeError(
                "PixAITaggerAdapter requires optional deps: "
                "pip install 'sceneweaver[vision]' (torch, transformers, Pillow)"
            ) from exc

        logger.info("loading PixAI tagger model_id=%s", self._model_id)
        # Official PixAI examples use trust_remote_code=True; confined to this adapter.
        self._processor = AutoImageProcessor.from_pretrained(
            self._model_id,
            trust_remote_code=True,
        )
        self._model = AutoModelForImageClassification.from_pretrained(
            self._model_id,
            trust_remote_code=True,
        )
        self._model.eval()
        return self._model, self._processor

    def _decode_tags(self, outputs: Any, processor: Any) -> list[ImageTag]:
        import torch  # type: ignore[import-untyped]

        logits = outputs.logits
        if hasattr(logits, "sigmoid"):
            probs = logits.sigmoid()[0]
        else:
            probs = torch.sigmoid(logits)[0]

        id2label = getattr(self._model.config, "id2label", {}) or {}
        category_map = getattr(self._model.config, "tag_category_map", None) or {}

        results: list[ImageTag] = []
        for idx, score in enumerate(probs.tolist()):
            if score < self._threshold:
                continue
            label = str(id2label.get(idx, id2label.get(str(idx), f"tag_{idx}")))
            category = str(category_map.get(label, category_map.get(idx, "general")))
            results.append(ImageTag(tag=label, category=category, score=float(score)))
        results.sort(key=lambda t: t.score, reverse=True)
        return results
