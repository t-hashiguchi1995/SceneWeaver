from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from creator_studio.domain.ids import ProjectId
from creator_studio.domain.project import Project
from creator_studio.infrastructure.db.models import ProjectRow
from creator_studio.infrastructure.db.repositories.mappers import project_from_row, project_to_row


class SqlAlchemyProjectRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, project: Project) -> Project:
        self._session.add(project_to_row(project))
        return project

    def get(self, project_id: ProjectId) -> Project | None:
        row = self._session.get(ProjectRow, str(project_id))
        return project_from_row(row) if row else None

    def list(self) -> list[Project]:
        rows = self._session.scalars(select(ProjectRow).order_by(ProjectRow.created_at.desc())).all()
        return [project_from_row(r) for r in rows]

    def save(self, project: Project) -> Project:
        row = self._session.get(ProjectRow, str(project.id))
        if row is None:
            return self.add(project)
        row.title = project.title
        row.status = project.status.value
        row.content_rating = project.content_rating
        row.updated_at = project.updated_at
        return project