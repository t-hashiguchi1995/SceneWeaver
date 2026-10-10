from __future__ import annotations

from typing import Protocol

from creator_studio.domain.ids import ProjectId
from creator_studio.domain.project import Project


class ProjectRepository(Protocol):
    def add(self, project: Project) -> Project: ...

    def get(self, project_id: ProjectId) -> Project | None: ...

    def list(self) -> list[Project]: ...

    def save(self, project: Project) -> Project: ...