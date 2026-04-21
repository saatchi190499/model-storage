import uuid

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import Response

from app.api.deps import get_commit_service
from app.schemas.dto import CommitVersionResponse, MessageResponse
from app.services.commit import CommitService

router = APIRouter(tags=["commit"])


@router.post("/commit/{project_id}", response_model=MessageResponse)
async def commit_to_project(
    project_id: uuid.UUID,
    file: UploadFile = File(...),
    message: str = Form(""),
    service: CommitService = Depends(get_commit_service),
) -> MessageResponse:
    payload = await file.read()
    service.process_zip_file(project_id=project_id, zip_bytes=payload, message=message, user_id=uuid.uuid4())
    return MessageResponse(message="the commit was successful")


@router.get("/project-files/{project_id}", response_model=list[str])
def list_project_files(
    project_id: uuid.UUID,
    service: CommitService = Depends(get_commit_service),
) -> list[str]:
    return service.list_project_file_paths(project_id)


@router.get("/project-file/{project_id}")
def download_project_file_by_path(
    project_id: uuid.UUID,
    path: str,
    service: CommitService = Depends(get_commit_service),
) -> Response:
    content = service.download_project_file_by_path(project_id, path)
    return Response(content=content, media_type="application/json")


@router.get("/{project_id:uuid}")
def download_files_by_project_id(
    project_id: uuid.UUID,
    service: CommitService = Depends(get_commit_service),
) -> Response:
    content = service.download_files_by_project_id(project_id)
    return Response(content=content, media_type="application/zip")


@router.get("/files/{commit_id}")
def download_files_at_commit(commit_id: int, service: CommitService = Depends(get_commit_service)) -> Response:
    content = service.download_files_at_commit(commit_id)
    return Response(content=content, media_type="application/zip")


@router.get("/commit/history/{project_id}", response_model=list[CommitVersionResponse])
def get_project_commit_history(
    project_id: uuid.UUID,
    service: CommitService = Depends(get_commit_service),
) -> list[CommitVersionResponse]:
    return [CommitVersionResponse(**item) for item in service.get_commits_by_project_id(project_id)]
