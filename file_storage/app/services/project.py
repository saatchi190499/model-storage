from uuid import UUID

from sqlalchemy.orm import Session

from app.repositories.project import ProjectRepository
from app.storage.local_storage import LocalStorage


class ProjectService:
    def __init__(self, db: Session, storage: LocalStorage) -> None:
        self.db = db
        self.storage = storage

    def create(self, field_id: UUID, name: str, description: str, is_private: bool) -> UUID:
        project_id = ProjectRepository.create(self.db, field_id, name, description, is_private)
        self.db.commit()
        return project_id

    def get_by_id(self, project_id: UUID) -> dict:
        return ProjectRepository.get_by_id(self.db, project_id)

    def update_by_id(self, project_id: UUID, values: dict[str, object]) -> None:
        ProjectRepository.update_by_id(self.db, project_id, values)
        self.db.commit()

    def delete_by_id(self, project_id: UUID) -> None:
        storage_keys = ProjectRepository.get_storage_keys_by_project_id(self.db, project_id)
        ProjectRepository.delete_by_id(self.db, project_id)
        self.db.commit()
        self.storage.delete_files(storage_keys)
        self.storage.delete_project_tree(str(project_id))

    def get_all_by_field_id(self, field_id: UUID) -> list[dict]:
        return ProjectRepository.get_all_by_field_id(self.db, field_id)

