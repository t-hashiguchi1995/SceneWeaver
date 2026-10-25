from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from creator_studio.application.prompt.renderer import PromptRenderer
from creator_studio.application.prompt.context import resolve_prompt_context
from creator_studio.domain.prompt import (
    ANIMA_COMPILER_LABEL,
    ANIMA_COMPILER_SOURCE_REF,
    MOSS_COMPILER_LABEL,
    MOSS_COMPILER_SOURCE_REF,
    PromptDraft,
    RenderedPrompt,
    compute_context_hash,
)
from creator_studio.ports.unit_of_work import UnitOfWork


@dataclass
class PromptDraftView:
    id: str
    shot_id: str
    template_id: str
    template_version: str
    source_kind: str
    source_ref: str
    template_label: str
    source_shot_revision: int
    context_hash: str
    rendered_base_positive: str
    rendered_base_negative: str
    edited_positive: str
    edited_negative: str
    modified: bool
    modified_positive: bool
    modified_negative: bool
    stale: bool
    assembly_metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


def capability_for_shot(shot: Any) -> str:
    return str((shot.render_spec or {}).get("capability") or "BaseRender")


class PromptDraftService:
    def __init__(self, uow: UnitOfWork, renderer: PromptRenderer | None = None) -> None:
        self._uow = uow
        self._renderer = renderer or PromptRenderer()

    def ensure_for_shot(self, shot_id: str) -> PromptDraftView:
        with self._uow as uow:
            shot = self._require_shot(uow, shot_id)
            rendered = self._render_for_shot(uow, shot)
            existing = uow.prompt_drafts.get_for_shot_template(
                shot.id, rendered.template_id, rendered.template_version
            )
            if existing is not None:
                if shot.current_prompt_draft_id != existing.id:
                    shot.current_prompt_draft_id = existing.id
                    uow.shots.save(shot)
                    uow.commit()
                return self._view(existing, shot)
            # Do not silent-overwrite a different current draft; create missing template draft.
            draft = PromptDraft.create(
                shot.id,
                template_id=rendered.template_id,
                template_version=rendered.template_version,
                source_kind=rendered.source_kind,
                source_ref=rendered.source_ref,
                source_shot_revision=shot.revision,
                context_hash=self._context_hash(shot, rendered.template_id, rendered.template_version),
                rendered_base_positive=rendered.positive,
                rendered_base_negative=rendered.negative,
            )
            draft.assembly_metadata = rendered.assembly_metadata
            uow.prompt_drafts.add(draft)
            shot.current_prompt_draft_id = draft.id
            uow.shots.save(shot)
            uow.commit()
            return self._view(draft, shot)

    def get_for_shot(self, shot_id: str) -> PromptDraftView:
        with self._uow as uow:
            shot = self._require_shot(uow, shot_id)
            return self._view(self._require_current_draft(uow, shot), shot)

    def update_edits(self, shot_id: str, positive: str, negative: str) -> PromptDraftView:
        with self._uow as uow:
            shot = self._require_shot(uow, shot_id)
            draft = self._require_current_draft(uow, shot)
            draft.set_edits(positive, negative)
            uow.prompt_drafts.save(draft)
            uow.commit()
            return self._view(draft, shot)

    def reset_edits(self, shot_id: str) -> PromptDraftView:
        with self._uow as uow:
            shot = self._require_shot(uow, shot_id)
            draft = self._require_current_draft(uow, shot)
            draft.reset_edits()
            uow.prompt_drafts.save(draft)
            uow.commit()
            return self._view(draft, shot)

    def rebuild(self, shot_id: str, *, confirm: bool = False) -> PromptDraftView:
        """Re-render from current ShotSpec into this draft (syncs edits to new base).

        When the draft has user edits, ``confirm=True`` is required so edits are
        never discarded silently.
        """
        with self._uow as uow:
            shot = self._require_shot(uow, shot_id)
            draft = self._require_current_draft(uow, shot)
            if draft.modified and not confirm:
                raise ValueError(
                    "prompt draft has user edits; pass confirm=true to discard and rebuild"
                )
            rendered = self._render_for_shot(uow, shot)
            if (
                draft.template_id != rendered.template_id
                or draft.template_version != rendered.template_version
            ):
                raise ValueError("template mismatch; create a new draft for this template")
            draft.rebuild_from_render(
                source_shot_revision=shot.revision,
                context_hash=self._context_hash(
                    shot, rendered.template_id, rendered.template_version
                ),
                rendered_base_positive=rendered.positive,
                rendered_base_negative=rendered.negative,
                sync_edits=True,
            )
            draft.assembly_metadata = rendered.assembly_metadata
            uow.prompt_drafts.save(draft)
            uow.commit()
            return self._view(draft, shot)

    def template_for_shot(self, shot_id: str) -> dict[str, Any]:
        with self._uow as uow:
            shot = self._require_shot(uow, shot_id)
            draft = self._current_draft(uow, shot)
            if draft is None:
                rendered = self._render_for_shot(uow, shot)
                return {
                    "source_kind": rendered.source_kind,
                    "source_ref": rendered.source_ref,
                    "label": rendered.label,
                    "body": self._renderer.describe_source(
                        rendered.source_kind, rendered.source_ref
                    ),
                }
            return {
                "source_kind": draft.source_kind,
                "source_ref": draft.source_ref,
                "label": self._label(draft),
                "body": self._renderer.describe_source(draft.source_kind, draft.source_ref),
            }

    def _render_for_shot(self, uow: UnitOfWork, shot: Any) -> RenderedPrompt:
        return self._renderer.render_for_capability(
            capability_for_shot(shot),
            resolve_prompt_context(uow, shot),
        )

    def _require_shot(self, uow: UnitOfWork, shot_id: str) -> Any:
        shot = uow.shots.get(shot_id)
        if shot is None:
            raise ValueError("shot not found")
        return shot

    def _require_current_draft(self, uow: UnitOfWork, shot: Any) -> PromptDraft:
        draft = self._current_draft(uow, shot)
        if draft is None:
            raise ValueError("prompt draft not found")
        return draft

    def _context_hash(self, shot: Any, template_id: str, template_version: str) -> str:
        return compute_context_hash(
            shot_revision=shot.revision,
            render_spec=resolve_prompt_context(self._uow, shot),
            template_id=template_id,
            template_version=template_version,
        )

    def _current_draft(self, uow: UnitOfWork, shot: Any) -> PromptDraft | None:
        if shot.current_prompt_draft_id:
            draft = uow.prompt_drafts.get(shot.current_prompt_draft_id)
            if draft is not None:
                return draft
        rendered = self._render_for_shot(uow, shot)
        return uow.prompt_drafts.get_for_shot_template(
            shot.id, rendered.template_id, rendered.template_version
        )

    def _view(self, draft: PromptDraft, shot: Any) -> PromptDraftView:
        current_hash = self._context_hash(shot, draft.template_id, draft.template_version)
        return PromptDraftView(
            id=draft.id,
            shot_id=str(draft.shot_id),
            template_id=draft.template_id,
            template_version=draft.template_version,
            source_kind=draft.source_kind,
            source_ref=draft.source_ref,
            template_label=self._label(draft),
            source_shot_revision=draft.source_shot_revision,
            context_hash=draft.context_hash,
            rendered_base_positive=draft.rendered_base_positive,
            rendered_base_negative=draft.rendered_base_negative,
            edited_positive=draft.edited_positive,
            edited_negative=draft.edited_negative,
            modified=draft.modified,
            modified_positive=draft.modified_positive,
            modified_negative=draft.modified_negative,
            stale=draft.is_stale(current_hash),
            assembly_metadata=draft.assembly_metadata,
        )

    def _label(self, draft: PromptDraft) -> str:
        if draft.source_ref == "default_prompt_builder_v1":
            return "Default Prompt Builder · Anima Story Panel v1"
        if draft.source_ref == MOSS_COMPILER_SOURCE_REF:
            return MOSS_COMPILER_LABEL
        if draft.source_ref == ANIMA_COMPILER_SOURCE_REF:
            return ANIMA_COMPILER_LABEL
        return f"{draft.source_kind}: {draft.source_ref}"
