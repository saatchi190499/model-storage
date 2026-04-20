from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import get_file_service
from app.schemas.dto import FileVersionHistoryResponse, GetFilesAtCommitResponse, ListFilesByProjectAndPathResponse
from app.services.file import FileService

router = APIRouter(prefix="/file", tags=["file"])


@router.get("/{project_id}", response_model=list[ListFilesByProjectAndPathResponse])
def get_files_by_project_id(
    project_id: UUID,
    path: str = "",
    service: FileService = Depends(get_file_service),
) -> list[ListFilesByProjectAndPathResponse]:
    return [ListFilesByProjectAndPathResponse(**item) for item in service.list_files_by_project_and_path(project_id, path)]


@router.get("/files/{commit_id}", response_model=list[GetFilesAtCommitResponse])
def get_files_at_commit(
    commit_id: int,
    service: FileService = Depends(get_file_service),
) -> list[GetFilesAtCommitResponse]:
    return [GetFilesAtCommitResponse(**item) for item in service.get_files_at_commit(commit_id)]


@router.get("/version-history/{file_version_id}", response_model=list[FileVersionHistoryResponse])
def get_version_history_by_file_version_id(
    file_version_id: int,
    service: FileService = Depends(get_file_service),
) -> list[FileVersionHistoryResponse]:
    return [FileVersionHistoryResponse(**item) for item in service.get_version_history_by_file_version_id(file_version_id)]
