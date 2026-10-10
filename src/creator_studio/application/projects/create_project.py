from __future__ import annotations

from dataclasses import dataclass

from creator_studio.domain.project import Project
from creator_studio.ports.unit_of_work import UnitOfWork


@dataclass
class CreateProjectCommand:
    title: str
    content_rating: str = "general"


@dataclass
class ProjectDTO:
    id: str
    title: str
    status: str
    content_rating: str
    created_at: str
    updated_at: str


def to_dto(project: Project) -> ProjectDTO:
    return ProjectDTO(
        id=str(project.id),
        title=project.title,
        status=project.status.value,
        content_rating=project.content_rating,
        created_at=project.created_at.isoformat(),
        updated_at=project.updated_at.isoformat(),
    )


class CreateProject:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, cmd: CreateProjectCommand) -> ProjectDTO:
        if not cmd.title.strip():
            raise ValueError("title is required")
        project = Project.create(cmd.title, cmd.content_rating)
        with self._uow as uow:
            uow.projects.add(project)
            uow.commit()
        return to_dto(project)


class ListProjects:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self) -> list[ProjectDTO]:
        with self._uow as uow:
            return [to_dto(p) for p in uow.projects.list()]


class GetProject:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, project_id: str) -> ProjectDTO | None:
        from creator_studio.domain.ids import ProjectId

        with self._uow as uow:
            project = uow.projects.get(ProjectId(project_id))
            return to_dto(project) if project else None