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
    accepted = settings.accepted_api_keys
    if not accepted:
        logger.error(
            "model-storage API key is not configured",
            extra={
                "event": "model_storage.auth.misconfigured",
                "path": request.url.path,
                "method": request.method,
                "client": _client_host(request),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="FILE_STORAGE_API_KEY is not configured",
        )

    matches = False
    if x_api_key:
        # Always compare against every configured key so rotation state is not exposed by timing.
        for expected in accepted:
            matches = hmac.compare_digest(x_api_key, expected) or matches
    if not matches:
        logger.warning(
            "model-storage API key denied",
            extra={
                "event": "model_storage.auth.denied",
                "path": request.url.path,
                "method": request.method,
                "client": _client_host(request),
                "has_key": bool(x_api_key),
            },
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


