from __future__ import annotations

from typing import Any

from creator_studio.domain.character.presets import ANIMA_RIZE_QUALITY_POSITIVE, ANIMA_RIZE_STYLE
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
        if render_spec.get("prompt_profile_id"):
            from creator_studio.application.prompt.assembly import build_default_prompt, components_from_context
            from creator_studio.domain.prompt.assembly import PromptAssemblyProfile
            profile_id = render_spec["prompt_profile_id"]
            if profile_id != "anima_story_panel" or render_spec.get("prompt_profile_version", "v1") != "v1":
                raise ValueError("unsupported prompt profile/version")
            profile = PromptAssemblyProfile()
            built = build_default_prompt(components_from_context(render_spec), profile)
            return RenderedPrompt(
                positive=built.positive, negative=built.negative,
                template_id=profile.profile_id, template_version=profile.profile_version,
                source_kind="compiler_rule", source_ref="default_prompt_builder_v1",
                label=f"Default Prompt Builder · Anima Story Panel v1 / {render_spec.get('prompt_quality_profile_id', 'builder_basic_v1')}",
                assembly_metadata={"prompt_profile_id": profile.profile_id,
                    "prompt_profile_version": profile.profile_version,
                    "prompt_quality_profile_id": render_spec.get('prompt_quality_profile_id', 'builder_basic_v1'),
                    "component_refs": [c.ref for c in built.components],
                    "components": [{"ref": c.ref, "kind": c.kind, "text": c.text} for c in built.components],
                    "model_modifiers": built.model_modifiers, "warnings": built.warnings},
            )
        identity = ",".join(render_spec.get("identity_tags", ["1girl"]))
        outfit = render_spec.get("outfit_tags", "casual clothes")
        expression = render_spec.get("expression", {}).get("id", "neutral")
        pose = render_spec.get("pose", {}).get("id", "standing")
        camera = render_spec.get("camera", {})
        positive = (
            f"{ANIMA_RIZE_QUALITY_POSITIVE}, {ANIMA_RIZE_STYLE}, {identity}, {outfit}, "
            f"{expression}, {pose}, "
            f"{camera.get('shot', 'medium')}, {camera.get('angle', 'eye_level')}"
        )
        for field in ("background", "lighting"):
            if render_spec.get(field):
                positive += f", {render_spec[field]}"
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
        if source_ref == "default_prompt_builder_v1":
            return "Default Prompt Builder v1: subject → identity → traits → outfit → expression → pose → camera → background → lighting → style → quality. Quality/style follows the selected builder_basic_v1 or anima_legacy_v1 preset. General content policy; stable precedence/priority/id conflict resolution."
        if source_kind == "compiler_rule" and source_ref == ANIMA_COMPILER_SOURCE_REF:
            return ANIMA_COMPILER_V1_DESCRIPTION
        return f"{source_kind}: {source_ref}"
