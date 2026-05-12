from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.repositories.commit import CommitRepository
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

    def delete_file_from_project(self, project_id: UUID, path: str, message: str) -> None:
        normalized_path = self._normalize_relative_path(path)
        if not normalized_path:
            raise HTTPException(status_code=400, detail="path is required")

        folder_path, file_name, file_format = self._split_file_path(normalized_path)
        target = FileRepository.get_active_by_project_path_name(self.db, project_id, folder_path, file_name, file_format)
        if target is None:
            raise HTTPException(status_code=404, detail=f"file not found: {normalized_path}")

        commit_message = message.strip() if message.strip() else f"delete {normalized_path}"
        commit_id = CommitRepository.create_commit(self.db, project_id, UUID(int=0), commit_message)

        deleted_files = [
            {
                "id": target["file_id"],
                "project_id": project_id,
                "name": target["name"],
                "file_format": target["file_format"],
                "path": target["path"],
                "last_file_version": {
                    "is_deleted": True,
                    "commit_id": commit_id,
                    "file_size": 0,
                    "hash": "",
                },
            }
        ]

        versions = CommitRepository.commit_files(self.db, changed_files=[], new_files=[], deleted_files=deleted_files)
        CommitRepository.update_file_versions(self.db, versions)
        CommitRepository.update_commit(self.db, project_id, commit_id)
        self.db.commit()

    @staticmethod
    def _normalize_relative_path(path: str) -> str:
        text = str(path or "").replace("\\", "/").strip().lstrip("/")
        if not text or text == ".":
            return ""
        parts = [part for part in text.split("/") if part and part != "."]
        if any(part == ".." for part in parts):
            raise HTTPException(status_code=400, detail="invalid path")
        return "/".join(parts)

    @staticmethod
    def _split_file_path(path: str) -> tuple[str, str, str]:
        parts = path.split("/")
        filename = parts[-1]
        if not filename:
            raise HTTPException(status_code=400, detail="path must target a file")

        dot_index = filename.rfind(".")
        if dot_index > 0:
            name = filename[:dot_index]
            file_format = filename[dot_index:]
        else:
            name = filename
            file_format = ""

        folder = "/".join(parts[:-1])
        return folder, name, file_format
