from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session


class FieldRepository:
    @staticmethod
    def create(db: Session, name: str, description: str) -> UUID:
        query = text(
            """
            insert into fields (name, description, created_at, updated_at)
            values (:name, :description, now(), now())
            returning id
            """
        )
        return db.execute(query, {"name": name, "description": description}).scalar_one()

    @staticmethod
    def get_by_id(db: Session, field_id: UUID) -> dict:
        query = text(
            """
            select id, name, description, created_at, updated_at, is_deleted
            from fields where id = :id
            """
        )
        row = db.execute(query, {"id": field_id}).mappings().first()
        if row is None:
            raise HTTPException(status_code=404, detail="field not found")
        if row["is_deleted"]:
            raise HTTPException(status_code=400, detail="the field is deleted")
        return dict(row)

    @staticmethod
    def update_by_id(db: Session, field_id: UUID, values: dict[str, object]) -> None:
        if not values:
            return
        allowed = {"name", "description"}
        unknown = set(values) - allowed
        if unknown:
            raise HTTPException(status_code=400, detail=f"field {unknown.pop()} is not allowed to be updated")

        assignments = ", ".join(f"{k} = :{k}" for k in values)
        params = {**values, "id": field_id}
        query = text(f"update fields set {assignments}, updated_at = now() where id = :id")
        result = db.execute(query, params)
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"no field found with id {field_id}")

    @staticmethod
    def delete_by_id(db: Session, field_id: UUID) -> None:
        query = text("update fields set is_deleted = true, updated_at = now() where id = :id")
        result = db.execute(query, {"id": field_id})
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="no field rows affected")

    @staticmethod
    def get_all(db: Session) -> list[dict]:
        query = text(
            """
            select id, name, description, created_at, updated_at, is_deleted
            from fields
            where is_deleted = false
            order by created_at desc
            """
        )
        rows = db.execute(query).mappings().all()
        return [dict(row) for row in rows]


