from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session


class ProjectRepository:
    @staticmethod
    def create(db: Session, field_id: UUID, name: str, description: str, is_private: bool) -> UUID:
        query = text(
            """
            insert into projects (field_id, name, description, is_private)
            values (:field_id, :name, :description, :is_private)
            returning id
            """
        )
        return db.execute(
            query,
            {"field_id": field_id, "name": name, "description": description, "is_private": is_private},
        ).scalar_one()

    @staticmethod
    def get_by_id(db: Session, project_id: UUID) -> dict:
        query = text(
            """
            select id, field_id, name, description, is_private, created_at, updated_at
            from projects where id = :id
            """
        )
        row = db.execute(query, {"id": project_id}).mappings().first()
        if row is None:
            raise HTTPException(status_code=404, detail="project not found")
        return dict(row)

    @staticmethod
    def update_by_id(db: Session, project_id: UUID, values: dict[str, object]) -> None:
        if not values:
            return
        allowed = {"name", "description", "is_private"}
        unknown = set(values) - allowed
        if unknown:
            raise HTTPException(status_code=400, detail=f"field {unknown.pop()} is not allowed to be updated")

        assignments = ", ".join(f"{k} = :{k}" for k in values)
        params = {**values, "id": project_id}
        query = text(f"update projects set {assignments}, updated_at = now() where id = :id")
        result = db.execute(query, params)
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"no project found with id {project_id}")

    @staticmethod
    def delete_by_id(db: Session, project_id: UUID) -> None:
        # Hard-delete project dependencies in FK-safe order, then remove project.
        db.execute(text("delete from project_members where project_id = :id"), {"id": project_id})
        db.execute(
            text(
                """
                delete from file_versions fv
                using files f
                where fv.file_id = f.id
                  and f.project_id = :id
                """
            ),
            {"id": project_id},
        )
        db.execute(text("delete from files where project_id = :id"), {"id": project_id})
        db.execute(text("delete from commits where project_id = :id"), {"id": project_id})

        query = text("delete from projects where id = :id")
        result = db.execute(query, {"id": project_id})
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="no rows affected")

    @staticmethod
    def get_storage_keys_by_project_id(db: Session, project_id: UUID) -> list[str]:
        query = text(
            """
            select distinct fv.storage_key
            from file_versions fv
            inner join files f on f.id = fv.file_id
            where f.project_id = :id
              and fv.storage_key is not null
            """
        )
        rows = db.execute(query, {"id": project_id}).mappings().all()
        return [str(row["storage_key"]) for row in rows if row.get("storage_key")]

    @staticmethod
    def get_all_by_field_id(db: Session, field_id: UUID) -> list[dict]:
        query = text(
            """
            select id, field_id, name, description, is_private, created_at, updated_at
            from projects where field_id = :field_id
            """
        )
        rows = db.execute(query, {"field_id": field_id}).mappings().all()
        return [dict(row) for row in rows]

