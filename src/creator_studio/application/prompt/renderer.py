from __future__ import annotations

from typing import Any

from creator_studio.domain.prompt import (
    ANIMA_COMPILER_ID,
    ANIMA_COMPILER_LABEL,
    ANIMA_COMPILER_SOURCE_REF,
    ANIMA_COMPILER_VERSION,
    RenderedPrompt,
)

# Human-readable description of the compiler rule shown in Template tab.
# This IS the source of truth for anima_compiler_v1 — not a decorative Jinja file.
ANIMA_COMPILER_V1_DESCRIPTION = """\
Anima Compiler v1 (programmatic rule)

Assembles positive / negative prompts from ShotSpec.render_spec:

  identity_tags  → joined character identity tags (default: 1girl)
  outfit_tags    → outfit fragment (default: casual clothes)
  expression.id  → expression token (default: neutral)
  pose.id        → pose token (default: standing)
  camera.shot    → framing (default: medium)
  camera.angle   → angle (default: eye_level)

Positive prefix includes quality / year / artist tags.
Negative includes common quality and anatomy reject tags.

Do not invent a separate Jinja template for this path —
the compiler rule above is what Generate actually uses.
"""


class PromptRenderer:
    """Single entry for Rendered Base. Template tab must match this source."""

    def render_anima(self, render_spec: dict[str, Any]) -> RenderedPrompt:
        identity = ",".join(render_spec.get("identity_tags", ["1girl"]))
        outfit = render_spec.get("outfit_tags", "casual clothes")
        expression = render_spec.get("expression", {}).get("id", "neutral")
        pose = render_spec.get("pose", {}).get("id", "standing")
        camera = render_spec.get("camera", {})
        positive = (
            "year 2025, newest, masterpiece, best quality, score_9, score_8, highres, "
            f"safe, @fuzichoco, @rella, {identity}, {outfit}, {expression}, {pose}, "
            f"{camera.get('shot', 'medium')}, {camera.get('angle', 'eye_level')}"
        )
        negative = (
            "worst quality, low quality, score_1, score_2, score_3, blurry, jpeg artifacts, "
            "sepia, bad anatomy, bad hands, text, error, missing fingers, extra digit, "
            "fewer digits, cropped, signature, watermark, username, artist name"
        )
        return RenderedPrompt(
            positive=positive,
            negative=negative,
            template_id=ANIMA_COMPILER_ID,
            template_version=ANIMA_COMPILER_VERSION,
            source_kind="compiler_rule",
            source_ref=ANIMA_COMPILER_SOURCE_REF,
            label=ANIMA_COMPILER_LABEL,
        )

    def describe_source(self, source_kind: str, source_ref: str) -> str:
        if source_kind == "compiler_rule" and source_ref == ANIMA_COMPILER_SOURCE_REF:
            return ANIMA_COMPILER_V1_DESCRIPTION
        return f"{source_kind}: {source_ref}"
