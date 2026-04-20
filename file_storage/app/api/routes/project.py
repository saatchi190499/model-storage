from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from app.api.deps import get_project_service
from app.schemas.dto import CreateProjectRequest, CreateProjectResponse, ProjectResponse
from app.services.project import ProjectService

router = APIRouter(prefix="/project", tags=["project"])


@router.post("/", response_model=CreateProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    request: CreateProjectRequest,
    service: ProjectService = Depends(get_project_service),
) -> CreateProjectResponse:
    return CreateProjectResponse(id=service.create(request.field_id, request.name, request.description, request.is_private))


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project_by_id(project_id: UUID, service: ProjectService = Depends(get_project_service)) -> ProjectResponse:
    return ProjectResponse(**service.get_by_id(project_id))


@router.patch("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def update_project_by_id(
    project_id: UUID,
    values: dict[str, object],
    service: ProjectService = Depends(get_project_service),
) -> Response:
    service.update_by_id(project_id, values)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project_by_id(project_id: UUID, service: ProjectService = Depends(get_project_service)) -> Response:
    service.delete_by_id(project_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/s/{field_id}", response_model=list[ProjectResponse])
def get_all_projects_by_field_id(
    field_id: UUID,
    service: ProjectService = Depends(get_project_service),
) -> list[ProjectResponse]:
    return [ProjectResponse(**item) for item in service.get_all_by_field_id(field_id)]

