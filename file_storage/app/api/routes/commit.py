import uuid

import mimetypes
import tempfile
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, Response
from starlette.background import BackgroundTask

from app.api.deps import get_commit_service
from app.core.config import settings
from app.schemas.dto import CommitVersionResponse, MessageResponse
from app.services.commit import CommitService

router = APIRouter(tags=["commit"])


async def _save_upload_to_temp_file(file: UploadFile, max_bytes: int) -> Path:
    temp_path: Path | None = None
    chunk_size = max(int(settings.stream_chunk_bytes), 64 * 1024)
    total = 0
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
            temp_path = Path(tmp.name)
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"Upload exceeds {max_bytes} bytes",
                    )
                tmp.write(chunk)

        if total == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")

        return temp_path
    except Exception:
        if temp_path and temp_path.exists():
            temp_path.unlink(missing_ok=True)
        raise


def _delete_temp_file(path: Path) -> None:
    path.unlink(missing_ok=True)


def _content_disposition(filename: str) -> str:
    fallback = filename.replace("\\", "_").replace("/", "_").replace('"', "").replace("\r", "").replace("\n", "")
    fallback = fallback.encode("ascii", "ignore").decode("ascii")
    if not fallback:
        fallback = "download"
    return f"attachment; filename=\"{fallback}\"; filename*=UTF-8''{quote(filename)}"


def _download_response(storage_path: Path, download_path: str, accel_redirect_path: str | None = None) -> Response:
    media_type = mimetypes.guess_type(download_path)[0] or "application/octet-stream"
    filename = Path(download_path).name
    if accel_redirect_path:
        return Response(
            status_code=status.HTTP_200_OK,
            media_type=media_type,
            headers={
                "X-Accel-Redirect": accel_redirect_path,
                "Content-Disposition": _content_disposition(filename),
                "X-Content-Type-Options": "nosniff",
            },
        )
    return FileResponse(storage_path, media_type=media_type, filename=filename)


@router.post("/commit/{project_id}", response_model=MessageResponse)
async def commit_to_project(
    project_id: uuid.UUID,
    file: UploadFile = File(...),
    message: str = Form(""),
    service: CommitService = Depends(get_commit_service),
) -> MessageResponse:
    zip_path = await _save_upload_to_temp_file(file, settings.max_upload_bytes)
    try:
        service.process_zip_file(project_id=project_id, zip_path=zip_path, message=message, user_id=uuid.uuid4())
    finally:
        _delete_temp_file(zip_path)
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
    storage_path, download_path, accel_redirect_path = service.get_project_file_download(project_id, path)
    return _download_response(storage_path, download_path, accel_redirect_path)


@router.get("/{project_id:uuid}")
def download_files_by_project_id(
    project_id: uuid.UUID,
    service: CommitService = Depends(get_commit_service),
) -> FileResponse:
    archive_path = service.create_project_archive(project_id)
    return FileResponse(
        archive_path,
        media_type="application/zip",
        filename=f"project-{project_id}.zip",
        background=BackgroundTask(_delete_temp_file, archive_path),
    )


@router.get("/files/{commit_id}")
def download_files_at_commit(commit_id: int, service: CommitService = Depends(get_commit_service)) -> FileResponse:
    archive_path = service.create_commit_archive(commit_id)
    return FileResponse(
        archive_path,
        media_type="application/zip",
        filename=f"commit-{commit_id}.zip",
        background=BackgroundTask(_delete_temp_file, archive_path),
    )


@router.get("/commit/history/{project_id}", response_model=list[CommitVersionResponse])
def get_project_commit_history(
    project_id: uuid.UUID,
    service: CommitService = Depends(get_commit_service),
) -> list[CommitVersionResponse]:
    return [CommitVersionResponse(**item) for item in service.get_commits_by_project_id(project_id)]
