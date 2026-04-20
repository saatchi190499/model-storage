from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.services.commit import CommitService
from app.services.file import FileService
from app.services.project import ProjectService
from app.services.field import FieldService
from app.storage.local_storage import LocalStorage


def get_field_service(db: Session = Depends(get_db)) -> FieldService:
    return FieldService(db)


def get_project_service(db: Session = Depends(get_db)) -> ProjectService:
    return ProjectService(db, LocalStorage(settings.storage_dir))


def get_file_service(db: Session = Depends(get_db)) -> FileService:
    return FileService(db)


def get_commit_service(db: Session = Depends(get_db)) -> CommitService:
    return CommitService(db, LocalStorage(settings.storage_dir))


