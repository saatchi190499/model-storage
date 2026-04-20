from uuid import UUID

from sqlalchemy.orm import Session

from app.repositories.file import FileRepository


class FileService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_files_by_project_and_path(self, project_id: UUID, path: str) -> list[dict]:
        return FileRepository.list_by_project_and_path(self.db, project_id, path)

    def get_files_at_commit(self, commit_id: int) -> list[dict]:
        return FileRepository.get_at_commit(self.db, commit_id)

    def get_version_history_by_file_version_id(self, file_version_id: int) -> list[dict]:
        return FileRepository.get_version_history_by_file_version_id(self.db, file_version_id)
