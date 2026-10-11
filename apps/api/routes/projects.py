from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from apps.api.deps import container
from apps.api.schemas import ProjectCreate, ProjectOut
from creator_studio.application.projects.create_project import CreateProjectCommand
from creator_studio.infrastructure.container import Container

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


@router.post("", response_model=ProjectOut)
def create_project(body: ProjectCreate, c: Container = Depends(container)) -> ProjectOut:
    dto = c.create_project().execute(
        CreateProjectCommand(title=body.title, content_rating=body.content_rating)
    )
    c.settings_service().touch_recent_project(dto.id)
    return ProjectOut(**dto.__dict__)


@router.get("", response_model=list[ProjectOut])
def list_projects(c: Container = Depends(container)) -> list[ProjectOut]:
    return [ProjectOut(**p.__dict__) for p in c.list_projects().execute()]


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: str, c: Container = Depends(container)) -> ProjectOut:
    dto = c.get_project().execute(project_id)
    if dto is None:
        raise HTTPException(status_code=404, detail="project not found")
    c.settings_service().touch_recent_project(project_id)
    return ProjectOut(**dto.__dict__)


@router.get("/{project_id}/dashboard")
def get_dashboard(project_id: str, c: Container = Depends(container)) -> dict:
    from creator_studio.application.projects.dashboard import ProjectDashboard
    try:
        return ProjectDashboard(c.uow(), c.csp_handoff()).get(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
