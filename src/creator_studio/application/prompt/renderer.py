from __future__ import annotations

from typing import Any

from creator_studio.application.prompt.anima_tags import (
    ANIMA_NEGATIVE,
    compile_anima_positive,
)
from creator_studio.application.prompt.assembly import build_default_prompt, components_from_context
from creator_studio.domain.prompt import (
    ANIMA_COMPILER_ID,
    ANIMA_COMPILER_LABEL,
    ANIMA_COMPILER_SOURCE_REF,
    ANIMA_COMPILER_VERSION,
    MOSS_COMPILER_ID,
    MOSS_COMPILER_LABEL,
    MOSS_COMPILER_SOURCE_REF,
    MOSS_COMPILER_VERSION,
    RenderedPrompt,
)
from creator_studio.domain.prompt.assembly import PromptAssemblyProfile

# Human-readable description of the compiler rule shown in Template tab.
# This IS the source of truth for anima_compiler_v1 — not a decorative Jinja file.
ANIMA_COMPILER_V1_DESCRIPTION = """\
Anima Compiler v1 (programmatic tag sequence)

Danbooru-style ordered slots (NOT natural-language captions — those are MOSS):

  quality → rating → subject → character_name → franchise →
  artist_style → identity → body → outfit → expression →
  pose → camera → background → lighting

Fields (ShotSpec.render_spec / Character Semantic Spec):

  subject_tags, character_name, franchise, artist_style_tags,
  identity_tags, body_tags, outfit_tags,
  expression.id, pose.id, camera.shot / camera.angle,
  background, lighting, content_rating / rating_profile

General fixtures use rating ``safe`` only.
Adult rating tokens (sensitive / nsfw / explicit) belong on the adult
rating profile for adult-declared original fixtures — never on standard
character smoke fixtures.

Default artists: @fuzichoco, @rella (overridable via artist_style_tags).
"""

MOSS_CAPTION_V1_DESCRIPTION = """\
MOSS Caption v1 (programmatic rule)

Assembles a natural-language caption for Stock MOSS-Image-SFT
(LayoutGuidedRender). Does NOT inject Anima-specific tokens:

  - no ``safe`` content tag
  - no ``@fuzichoco`` / ``@rella`` artist tags
  - no year / masterpiece / score_* quality stack

Fields (from ShotSpec.render_spec / resolved context):

  identity_tags, character_traits, outfit_tags,
  expression.id, pose.id, camera.shot / camera.angle,
  background, lighting

Adult projects omit ``nsfw`` from the negative prompt so R-18 baselines
are not poisoned by general-safety negatives.
"""

# Tokens that must never appear on the MOSS caption path (Anima pollution).
# ``safe,`` (with comma) avoids false positives on unrelated words containing "safe".
_ANIMA_POLLUTION_MARKERS = ("safe,", "@fuzichoco", "@rella", "score_9", "masterpiece")

# Shared core; adult path omits leading ``nsfw`` so R-18 baselines are not poisoned.
_MOSS_NEGATIVE_CORE = (
    "worst quality, bad anatomy, bad hands, watermark, jpeg artifacts, "
    "text, error, logo, signature"
)


class PromptRenderer:
    """Single entry for Rendered Base. Template tab must match this source."""

    def render_for_capability(self, capability: str, render_spec: dict[str, Any]) -> RenderedPrompt:
        """Route prompt assembly by ImageBackend capability.

        LayoutGuidedRender → MOSS caption (no Anima artist/quality/safe tokens).
        Everything else (BaseRender, PoseControlledRender, …) → Anima path.
        """
        if capability == "LayoutGuidedRender":
            return self.render_moss(render_spec)
        return self.render_anima(render_spec)

    def render_anima(self, render_spec: dict[str, Any]) -> RenderedPrompt:
        if render_spec.get("prompt_profile_id"):
            profile_id = render_spec["prompt_profile_id"]
            if profile_id != "anima_story_panel" or render_spec.get("prompt_profile_version", "v1") != "v1":
                raise ValueError("unsupported prompt profile/version")
            profile = PromptAssemblyProfile()
            built = build_default_prompt(components_from_context(render_spec), profile)
            quality_id = render_spec.get("prompt_quality_profile_id", "builder_basic_v1")
            return RenderedPrompt(
                positive=built.positive,
                negative=built.negative,
                template_id=profile.profile_id,
                template_version=profile.profile_version,
                source_kind="compiler_rule",
                source_ref="default_prompt_builder_v1",
                label=f"Default Prompt Builder · Anima Story Panel v1 / {quality_id}",
                assembly_metadata={
                    "prompt_profile_id": profile.profile_id,
                    "prompt_profile_version": profile.profile_version,
                    "prompt_quality_profile_id": quality_id,
                    "component_refs": [c.ref for c in built.components],
                    "components": [
                        {"ref": c.ref, "kind": c.kind, "text": c.text} for c in built.components
                    ],
                    "model_modifiers": built.model_modifiers,
                    "warnings": built.warnings,
                },
            )
        # Gate 2.6 adopted Character Prompt — prefer over auto-compile when present.
        saved = str(render_spec.get("_saved_anima_positive") or "").strip()
        if saved:
            return RenderedPrompt(
                positive=saved,
                negative=ANIMA_NEGATIVE,
                template_id=ANIMA_COMPILER_ID,
                template_version=ANIMA_COMPILER_VERSION,
                source_kind="compiler_rule",
                source_ref=ANIMA_COMPILER_SOURCE_REF,
                label=f"{ANIMA_COMPILER_LABEL} · saved character prompt",
                assembly_metadata={
                    "compiler": "anima_saved_character_prompt",
                    "content_rating": str(render_spec.get("content_rating") or "general"),
                    "character_name": str(render_spec.get("character_name") or ""),
                    "franchise": str(render_spec.get("franchise") or ""),
                    "saved_anima_positive": True,
                },
            )
        positive = compile_anima_positive(render_spec)
        return RenderedPrompt(
            positive=positive,
            negative=ANIMA_NEGATIVE,
            template_id=ANIMA_COMPILER_ID,
            template_version=ANIMA_COMPILER_VERSION,
            source_kind="compiler_rule",
            source_ref=ANIMA_COMPILER_SOURCE_REF,
            label=ANIMA_COMPILER_LABEL,
            assembly_metadata={
                "compiler": "anima_tag_sequence",
                "content_rating": str(render_spec.get("content_rating") or "general"),
                "character_name": str(render_spec.get("character_name") or ""),
                "franchise": str(render_spec.get("franchise") or ""),
            },
        )

    def render_moss(self, render_spec: dict[str, Any]) -> RenderedPrompt:
        """Natural-language caption for Stock MOSS-Image-SFT.

        Intentionally ignores ``prompt_profile_id`` (Anima Story Panel) so adult /
        multi-entity baselines are not polluted by ``safe`` / artist tags.
        """
        identity = ", ".join(render_spec.get("identity_tags") or ["1girl"])
        traits = str(render_spec.get("character_traits") or "").strip()
        outfit = render_spec.get("outfit_tags") or "casual clothes"
        expression = _spec_id(render_spec.get("expression"), "neutral")
        pose = _spec_id(render_spec.get("pose"), "standing")
        raw_camera = render_spec.get("camera")
        camera = raw_camera if isinstance(raw_camera, dict) else {}
        shot = camera.get("shot", "medium")
        angle = camera.get("angle", "eye_level")

        subject = f"Illustration of {identity}"
        if traits:
            subject = f"{subject}, {traits}"
        clauses = [
            subject,
            f"wearing {outfit}",
            f"{expression} expression",
            f"{pose} pose",
            f"{shot} shot",
            f"{angle} angle",
        ]
        for field in ("background", "lighting"):
            value = render_spec.get(field)
            if value:
                clauses.append(str(value))
        positive = ", ".join(clauses)
        _reject_anima_pollution(positive)

        content_rating = str(render_spec.get("content_rating") or "general")
        return RenderedPrompt(
            positive=positive,
            negative=_moss_negative(content_rating),
            template_id=MOSS_COMPILER_ID,
            template_version=MOSS_COMPILER_VERSION,
            source_kind="compiler_rule",
            source_ref=MOSS_COMPILER_SOURCE_REF,
            label=MOSS_COMPILER_LABEL,
            assembly_metadata={
                "capability": "LayoutGuidedRender",
                "content_rating": content_rating,
            },
        )

    def describe_source(self, source_kind: str, source_ref: str) -> str:
        if source_ref == "default_prompt_builder_v1":
            return (
                "Default Prompt Builder v1: subject → identity → traits → outfit → "
                "expression → pose → camera → background → lighting → style → quality. "
                "Quality/style follows the selected builder_basic_v1 or anima_legacy_v1 "
                "preset. General content policy; stable precedence/priority/id conflict "
                "resolution."
            )
        if source_kind == "compiler_rule" and source_ref == ANIMA_COMPILER_SOURCE_REF:
            return ANIMA_COMPILER_V1_DESCRIPTION
        if source_kind == "compiler_rule" and source_ref == MOSS_COMPILER_SOURCE_REF:
            return MOSS_CAPTION_V1_DESCRIPTION
        return f"{source_kind}: {source_ref}"


def _moss_negative(content_rating: str) -> str:
    """Adult omits ``nsfw`` so it does not fight R-18 Stock baselines."""
    if content_rating == "adult":
        return _MOSS_NEGATIVE_CORE
    return f"nsfw, {_MOSS_NEGATIVE_CORE}"


def _reject_anima_pollution(positive: str) -> None:
    lowered = positive.lower()
    for marker in _ANIMA_POLLUTION_MARKERS:
        if marker.lower() in lowered:
            raise ValueError(f"MOSS caption must not contain Anima token: {marker}")


def _spec_id(value: Any, default: str) -> str:
    if isinstance(value, dict):
        return str(value.get("id") or default)
    if isinstance(value, str) and value:
        return value
    return default
