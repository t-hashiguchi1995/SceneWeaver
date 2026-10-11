from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from creator_studio.domain.ids import ShotId
from creator_studio.domain.prompt import PromptDraft
from creator_studio.infrastructure.db.models.prompt import (
    LegacyImportRecordRow,
    PromptDraftRow,
    PromptPresetRow,
)


class SqlAlchemyPromptDraftRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, draft: PromptDraft) -> PromptDraft:
        self._session.add(self._to_row(draft))
        return draft

    def get(self, draft_id: str) -> PromptDraft | None:
        row = self._session.get(PromptDraftRow, draft_id)
        return self._from_row(row) if row else None

    def get_for_shot_template(
        self, shot_id: ShotId | str, template_id: str, template_version: str
    ) -> PromptDraft | None:
        row = self._session.scalars(
            select(PromptDraftRow).where(
                PromptDraftRow.shot_id == str(shot_id),
                PromptDraftRow.template_id == template_id,
                PromptDraftRow.template_version == template_version,
            )
        ).first()
        return self._from_row(row) if row else None

    def save(self, draft: PromptDraft) -> PromptDraft:
        row = self._session.get(PromptDraftRow, draft.id)
        if row is None:
            return self.add(draft)
        fresh = self._to_row(draft)
        row.source_shot_revision = fresh.source_shot_revision
        row.context_hash = fresh.context_hash
        row.rendered_base_positive = fresh.rendered_base_positive
        row.rendered_base_negative = fresh.rendered_base_negative
        row.edited_positive = fresh.edited_positive
        row.edited_negative = fresh.edited_negative
        row.assembly_metadata_json = fresh.assembly_metadata_json
        row.updated_at = fresh.updated_at
        return draft

    def _to_row(self, draft: PromptDraft) -> PromptDraftRow:
        return PromptDraftRow(
            id=draft.id,
            shot_id=str(draft.shot_id),
            template_id=draft.template_id,
            template_version=draft.template_version,
            source_kind=draft.source_kind,
            source_ref=draft.source_ref,
            source_shot_revision=draft.source_shot_revision,
            context_hash=draft.context_hash,
            rendered_base_positive=draft.rendered_base_positive,
            rendered_base_negative=draft.rendered_base_negative,
            edited_positive=draft.edited_positive,
            edited_negative=draft.edited_negative,
            assembly_metadata_json=draft.assembly_metadata,
            created_at=draft.created_at,
            updated_at=draft.updated_at,
        )

    def _from_row(self, row: PromptDraftRow) -> PromptDraft:
        return PromptDraft(
            id=row.id,
            shot_id=ShotId(row.shot_id),
            template_id=row.template_id,
            template_version=row.template_version,
            source_kind=row.source_kind,  # type: ignore[arg-type]
            source_ref=row.source_ref,
            source_shot_revision=row.source_shot_revision,
            context_hash=row.context_hash,
            rendered_base_positive=row.rendered_base_positive,
            rendered_base_negative=row.rendered_base_negative,
            edited_positive=row.edited_positive,
            edited_negative=row.edited_negative,
            assembly_metadata=dict(row.assembly_metadata_json or {}),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )


class SqlAlchemyPromptPresetRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_legacy(
        self, source: str, source_file: str, legacy_key: str
    ) -> PromptPresetRow | None:
        return self._session.scalars(
            select(PromptPresetRow).where(
                PromptPresetRow.source == source,
                PromptPresetRow.source_file == source_file,
                PromptPresetRow.legacy_key == legacy_key,
            )
        ).first()

    def add_row(self, row: PromptPresetRow) -> PromptPresetRow:
        self._session.add(row)
        return row

    def list_enabled(self) -> list[PromptPresetRow]:
        return list(self._session.scalars(select(PromptPresetRow).where(
            PromptPresetRow.enabled.is_(True), PromptPresetRow.kind != 'category_label'
        ).order_by(PromptPresetRow.source_file, PromptPresetRow.legacy_key)).all())

    def list_by_kind(self, kind: str) -> list[PromptPresetRow]:
        return list(
            self._session.scalars(
                select(PromptPresetRow).where(
                    PromptPresetRow.kind == kind,
                    PromptPresetRow.enabled.is_(True),
                )
            ).all()
        )


class SqlAlchemyLegacyImportRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, source: str, source_file: str, legacy_key: str) -> LegacyImportRecordRow | None:
        return self._session.scalars(
            select(LegacyImportRecordRow).where(
                LegacyImportRecordRow.source == source,
                LegacyImportRecordRow.source_file == source_file,
                LegacyImportRecordRow.legacy_key == legacy_key,
            )
        ).first()

    def add(self, row: LegacyImportRecordRow) -> LegacyImportRecordRow:
        self._session.add(row)
        return row
