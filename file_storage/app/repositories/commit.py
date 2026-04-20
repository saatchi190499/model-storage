from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session


class CommitRepository:
    @staticmethod
    def create_commit(db: Session, project_id: UUID, user_id: UUID, message: str) -> int:
        query = text(
            """
            insert into commits (project_id, message, user_id, created_at, updated_at)
            values (:project_id, :message, :user_id, now(), now())
            returning id
            """
        )
        return db.execute(query, {"project_id": project_id, "message": message, "user_id": user_id}).scalar_one()

    @staticmethod
    def get_files_by_project_id(db: Session, project_id: UUID, active_only: bool = False) -> list[dict]:
        where_active = "and fv.is_deleted = false" if active_only else ""
        query = text(
            f"""
            select f.id as file_id, f.project_id, f.name, f.file_format, f.path,
                   fv.id as file_version_id, fv.storage_key, fv.file_size, fv.hash,
                   fv.version, fv.commit_id, fv.is_deleted, fv.created_at, fv.updated_at
            from files f
            left join file_versions fv on f.last_file_version_id = fv.id
            where f.project_id = :project_id {where_active}
            """
        )
        rows = db.execute(query, {"project_id": project_id}).mappings().all()
        return [dict(row) for row in rows]

    @staticmethod
    def commit_files(db: Session, changed_files: list[dict], new_files: list[dict], deleted_files: list[dict]) -> list[dict]:
        file_versions: list[dict] = []

        get_last_version = text("select coalesce(max(version), 0) from file_versions where file_id = :file_id")
        insert_file_version = text(
            """
            insert into file_versions (file_id, version, file_size, hash, commit_id, is_deleted)
            values (:file_id, :version, :file_size, :hash, :commit_id, :is_deleted)
            returning id
            """
        )
        insert_file = text(
            """
            insert into files (project_id, name, file_format, path)
            values (:project_id, :name, :file_format, :path)
            returning id
            """
        )
        update_file_meta = text(
            """
            update files
            set name = :name, file_format = :file_format, path = :path, updated_at = now()
            where id = :file_id
            """
        )

        for file in changed_files + deleted_files:
            if not file["last_file_version"]["is_deleted"]:
                db.execute(
                    update_file_meta,
                    {
                        "file_id": file["id"],
                        "name": file["name"],
                        "file_format": file["file_format"],
                        "path": file["path"],
                    },
                )

            last_version = db.execute(get_last_version, {"file_id": file["id"]}).scalar_one()
            file_version_id = db.execute(
                insert_file_version,
                {
                    "file_id": file["id"],
                    "version": last_version + 1,
                    "file_size": file["last_file_version"]["file_size"],
                    "hash": file["last_file_version"]["hash"],
                    "commit_id": file["last_file_version"]["commit_id"],
                    "is_deleted": file["last_file_version"]["is_deleted"],
                },
            ).scalar_one()
            file_versions.append(
                {
                    "file_id": file["id"],
                    "project_id": file["project_id"],
                    "name": file["name"],
                    "file_format": file["file_format"],
                    "path": file["path"],
                    "file_version_id": file_version_id,
                    "version": last_version + 1,
                    "commit_id": file["last_file_version"]["commit_id"],
                    "is_deleted": file["last_file_version"]["is_deleted"],
                }
            )

        for file in new_files:
            file_id = db.execute(
                insert_file,
                {
                    "project_id": file["project_id"],
                    "name": file["name"],
                    "file_format": file["file_format"],
                    "path": file["path"],
                },
            ).scalar_one()
            file_version_id = db.execute(
                insert_file_version,
                {
                    "file_id": file_id,
                    "version": 1,
                    "file_size": file["last_file_version"]["file_size"],
                    "hash": file["last_file_version"]["hash"],
                    "commit_id": file["last_file_version"]["commit_id"],
                    "is_deleted": file["last_file_version"]["is_deleted"],
                },
            ).scalar_one()
            file_versions.append(
                {
                    "file_id": file_id,
                    "project_id": file["project_id"],
                    "name": file["name"],
                    "file_format": file["file_format"],
                    "path": file["path"],
                    "file_version_id": file_version_id,
                    "version": 1,
                    "commit_id": file["last_file_version"]["commit_id"],
                    "is_deleted": file["last_file_version"]["is_deleted"],
                }
            )

        return file_versions

    @staticmethod
    def update_file_versions(db: Session, file_versions: list[dict]) -> None:
        update_file_version = text("update file_versions set storage_key = :storage_key, updated_at = now() where id = :id")
        update_file = text("update files set last_file_version_id = :version_id, updated_at = now() where id = :file_id")

        for version in file_versions:
            result = db.execute(update_file_version, {"storage_key": version.get("storage_key"), "id": version["file_version_id"]})
            if result.rowcount == 0:
                raise HTTPException(status_code=500, detail="no file version rows affected")

            result = db.execute(update_file, {"version_id": version["file_version_id"], "file_id": version["file_id"]})
            if result.rowcount == 0:
                raise HTTPException(status_code=500, detail="no file rows affected")

    @staticmethod
    def update_commit(db: Session, project_id: UUID, commit_id: int) -> None:
        parent_query = text(
            """
            select id
            from commits
            where project_id = :project_id and id != :commit_id and is_complete = true
            order by created_at desc
            limit 1
            """
        )
        parent_id = db.execute(parent_query, {"project_id": project_id, "commit_id": commit_id}).scalar_one_or_none()
        if parent_id is None:
            db.execute(
                text("update commits set parent_commit_id = null, is_complete = true, updated_at = now() where id = :id"),
                {"id": commit_id},
            )
            return

        result = db.execute(
            text(
                """
                update commits
                set parent_commit_id = :parent_id, is_complete = true, updated_at = now()
                where id = :commit_id
                """
            ),
            {"parent_id": parent_id, "commit_id": commit_id},
        )
        if result.rowcount == 0:
            raise HTTPException(status_code=500, detail="no commit rows affected")

    @staticmethod
    def delete_commit(db: Session, commit_id: int) -> None:
        result = db.execute(text("delete from commits where id = :id"), {"id": commit_id})
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="no rows affected")

    @staticmethod
    def get_files_at_commit(db: Session, commit_id: int) -> list[dict]:
        query = text(
            """
            with target_commit as (
                select project_id, created_at from commits where id = :commit_id
            ),
            latest_version as (
                select fv.*
                from file_versions fv
                inner join files f on f.id = fv.file_id
                inner join commits c on c.id = fv.commit_id
                inner join target_commit tc on tc.project_id = f.project_id
                where c.created_at <= tc.created_at
                  and f.project_id = tc.project_id
                  and c.is_complete = true
                  and fv.is_deleted = false
                  and not exists (
                      select 1
                      from file_versions fv2
                      inner join commits c2 on c2.id = fv2.commit_id
                      where fv2.file_id = fv.file_id
                        and c2.created_at <= tc.created_at
                        and fv2.version > fv.version
                  )
            )
            select f.id as file_id, f.project_id, f.name, f.file_format, f.path,
                   lv.id as file_version_id, lv.storage_key, lv.file_size, lv.hash,
                   lv.version, lv.commit_id, lv.is_deleted, lv.created_at, lv.updated_at
            from latest_version lv
            inner join files f on f.id = lv.file_id
            """
        )
        rows = db.execute(query, {"commit_id": commit_id}).mappings().all()
        return [dict(row) for row in rows]

    @staticmethod
    def get_commits_by_project_id(db: Session, project_id: UUID) -> list[dict]:
        query = text(
            """
            select id, message, user_id, is_complete, created_at
            from commits
            where project_id = :project_id
              and is_complete = true
            order by created_at desc, id desc
            """
        )
        rows = db.execute(query, {"project_id": project_id}).mappings().all()
        return [dict(row) for row in rows]
