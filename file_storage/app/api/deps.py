import hmac
import logging

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.services.commit import CommitService
from app.services.file import FileService
from app.services.project import ProjectService
from app.services.field import FieldService
from app.storage.local_storage import LocalStorage

logger = logging.getLogger("model_storage.auth")


def _client_host(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def require_api_key(request: Request, x_api_key: str | None = Header(default=None)) -> None:
    expected = settings.api_key.strip()
    if not expected:
        logger.error(
            "model_storage.auth.misconfigured path=%s method=%s client=%s",
            request.url.path,
            request.method,
            _client_host(request),
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="FILE_STORAGE_API_KEY is not configured",
        )
    if not x_api_key or not hmac.compare_digest(x_api_key, expected):
        logger.warning(
            "model_storage.auth.denied path=%s method=%s client=%s has_key=%s",
            request.url.path,
            request.method,
            _client_host(request),
            bool(x_api_key),
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")


def get_field_service(db: Session = Depends(get_db)) -> FieldService:
    return FieldService(db)


def get_project_service(db: Session = Depends(get_db)) -> ProjectService:
    return ProjectService(db, LocalStorage(settings.storage_dir))


def get_file_service(db: Session = Depends(get_db)) -> FileService:
    return FileService(db)


def get_commit_service(db: Session = Depends(get_db)) -> CommitService:
    return CommitService(db, LocalStorage(settings.storage_dir))


