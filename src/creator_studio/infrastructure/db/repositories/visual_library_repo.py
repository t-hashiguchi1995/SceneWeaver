from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from creator_studio.infrastructure.db.models.visual_library import VisualLibraryMetadataRow


class SqlAlchemyVisualLibraryMetadataRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, source_type: str, source_id: str) -> VisualLibraryMetadataRow | None:
        return self._session.scalars(
            select(VisualLibraryMetadataRow).where(
                VisualLibraryMetadataRow.source_type == source_type,
                VisualLibraryMetadataRow.source_id == source_id,
            )
        ).first()

    def get_by_id(self, metadata_id: str) -> VisualLibraryMetadataRow | None:
        return self._session.get(VisualLibraryMetadataRow, metadata_id)

    def add(self, row: VisualLibraryMetadataRow) -> VisualLibraryMetadataRow:
        self._session.add(row)
        return row

    def upsert(self, row: VisualLibraryMetadataRow) -> VisualLibraryMetadataRow:
        existing = self.get(row.source_type, row.source_id)
        if existing is None:
            return self.add(row)
        existing.visual_kind = row.visual_kind
        existing.label_ja = row.label_ja
        existing.description_ja = row.description_ja
        existing.thumbnail_asset_id = row.thumbnail_asset_id
        existing.preview_kind = row.preview_kind
        existing.subcategory = row.subcategory
        existing.tags_json = row.tags_json
        existing.model_scope_json = row.model_scope_json
        existing.related_refs_json = row.related_refs_json
        existing.updated_at = row.updated_at
        return existing

    def list_all(self) -> list[VisualLibraryMetadataRow]:
        return list(self._session.scalars(select(VisualLibraryMetadataRow)).all())

    def map_by_source(self) -> dict[tuple[str, str], VisualLibraryMetadataRow]:
        return {(row.source_type, row.source_id): row for row in self.list_all()}
