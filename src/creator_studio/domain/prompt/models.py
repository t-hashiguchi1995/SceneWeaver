from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

from creator_studio.domain.ids import ShotId, new_id
from creator_studio.domain.timeutil import utc_now

SourceKind = Literal["jinja", "compiler_rule"]

ANIMA_COMPILER_ID = "anima_compiler"
ANIMA_COMPILER_VERSION = "v1"
ANIMA_COMPILER_SOURCE_REF = "anima_compiler_v1"
ANIMA_COMPILER_LABEL = "生成ルール: Anima Compiler v1"

# Stock MOSS-Image-SFT caption path (LayoutGuidedRender). No Anima artist/quality tokens.
MOSS_COMPILER_ID = "moss_caption"
MOSS_COMPILER_VERSION = "v1"
MOSS_COMPILER_SOURCE_REF = "moss_caption_v1"
MOSS_COMPILER_LABEL = "生成ルール: MOSS Caption v1"


def compute_prompt_hash(positive: str, negative: str) -> str:
    """ADR 0010: hash finals byte-for-byte as submitted to ImageBackend.

    Do not strip, Unicode-normalize, rewrite newlines, or reorder tags solely for
    hashing — callers must pass the same strings sent to the backend.
    """
    return hashlib.sha256(
        positive.encode("utf-8") + b"\x00" + negative.encode("utf-8")
    ).hexdigest()


def compute_context_hash(
    *,
    shot_revision: int,
    render_spec: dict[str, Any],
    template_id: str,
    template_version: str,
) -> str:
    """ADR 0010: hash of resolved prompt-affecting semantic context.

    ``render_spec`` MUST already include every Character / Outfit / Pose /
    Expression / Style (etc.) input the compiler reads; otherwise stale detection
    will miss real prompt drift.
    """
    payload = {
        "shot_revision": shot_revision,
        "render_spec": render_spec,
        "template_id": template_id,
        "template_version": template_version,
    }
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass
class PromptDraft:
    id: str
    shot_id: ShotId
    template_id: str
    template_version: str
    source_kind: SourceKind
    source_ref: str
    source_shot_revision: int
    context_hash: str
    rendered_base_positive: str
    rendered_base_negative: str
    edited_positive: str
    edited_negative: str
    assembly_metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    @classmethod
    def create(
        cls,
        shot_id: ShotId,
        *,
        template_id: str,
        template_version: str,
        source_kind: SourceKind,
        source_ref: str,
        source_shot_revision: int,
        context_hash: str,
        rendered_base_positive: str,
        rendered_base_negative: str,
    ) -> PromptDraft:
        now = utc_now()
        return cls(
            id=new_id(),
            shot_id=shot_id,
            template_id=template_id,
            template_version=template_version,
            source_kind=source_kind,
            source_ref=source_ref,
            source_shot_revision=source_shot_revision,
            context_hash=context_hash,
            rendered_base_positive=rendered_base_positive,
            rendered_base_negative=rendered_base_negative,
            edited_positive=rendered_base_positive,
            edited_negative=rendered_base_negative,
            created_at=now,
            updated_at=now,
        )

    @property
    def modified_positive(self) -> bool:
        return self.edited_positive != self.rendered_base_positive

    @property
    def modified_negative(self) -> bool:
        return self.edited_negative != self.rendered_base_negative

    @property
    def modified(self) -> bool:
        return self.modified_positive or self.modified_negative

    def is_stale(self, current_context_hash: str) -> bool:
        return self.context_hash != current_context_hash

    def set_edits(self, positive: str, negative: str) -> None:
        self.edited_positive = positive
        self.edited_negative = negative
        self.updated_at = utc_now()

    def reset_edits(self) -> None:
        self.edited_positive = self.rendered_base_positive
        self.edited_negative = self.rendered_base_negative
        self.updated_at = utc_now()

    def rebuild_from_render(
        self,
        *,
        source_shot_revision: int,
        context_hash: str,
        rendered_base_positive: str,
        rendered_base_negative: str,
        sync_edits: bool = True,
    ) -> None:
        self.source_shot_revision = source_shot_revision
        self.context_hash = context_hash
        self.rendered_base_positive = rendered_base_positive
        self.rendered_base_negative = rendered_base_negative
        if sync_edits:
            self.edited_positive = rendered_base_positive
            self.edited_negative = rendered_base_negative
        self.updated_at = utc_now()


@dataclass
class RenderedPrompt:
    positive: str
    negative: str
    template_id: str
    template_version: str
    source_kind: SourceKind
    source_ref: str
    label: str
    assembly_metadata: dict[str, Any] = field(default_factory=dict)
