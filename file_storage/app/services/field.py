from uuid import UUID

from sqlalchemy.orm import Session

from app.repositories.field import FieldRepository


class FieldService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, name: str, description: str) -> UUID:
        field_id = FieldRepository.create(self.db, name, description)
        self.db.commit()
        return field_id

    def get_by_id(self, field_id: UUID) -> dict:
        return FieldRepository.get_by_id(self.db, field_id)

    def update_by_id(self, field_id: UUID, values: dict[str, object]) -> None:
        FieldRepository.update_by_id(self.db, field_id, values)
        self.db.commit()

    def delete_by_id(self, field_id: UUID) -> None:
        FieldRepository.delete_by_id(self.db, field_id)
        self.db.commit()

    def get_all(self) -> list[dict]:
        return FieldRepository.get_all(self.db)


