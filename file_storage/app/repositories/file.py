from sqlalchemy import text
from sqlalchemy.orm import Session
from uuid import UUID


class FileRepository:
    @staticmethod
    def list_by_project_and_path(db: Session, project_id: UUID, path: str) -> list[dict]:
        query = text(
            """
            with immediate_subfolders as (
                select distinct
                    split_part(
                        case
                            when :path = '' then f.path
                            else substring(f.path from length(:path) + 2)
                        end,
                        '/',
                        1
                    ) as name
                from files f
                where f.project_id = :project_id
                  and f.path like case when :path = '' then '%' else :path || '/%' end
            ),
            files_in_folder as (
                select fv.id as file_version_id, f.name, f.file_format, fv.updated_at
                from files f
                left join file_versions fv on f.last_file_version_id = fv.id
                where f.project_id = :project_id
                  and fv.is_deleted = false
                  and f.path = :path
            )
            select null::int as file_version_id, name, 'folder' as file_format, null::timestamptz as updated_at, 'folder' as type from immediate_subfolders
            union all
            select file_version_id, name, file_format, updated_at, 'file' as type from files_in_folder
            order by type desc, name
            """
        )
        rows = db.execute(query, {"project_id": project_id, "path": path}).mappings().all()
        return [dict(row) for row in rows]

    @staticmethod
    def get_at_commit(db: Session, commit_id: int) -> list[dict]:
        query = text(
            """
            select fv.id as file_version_id, f.name, f.file_format, fv.updated_at
            from files f
            inner join file_versions fv on f.id = fv.file_id
            where fv.commit_id = :commit_id
            """
        )
        rows = db.execute(query, {"commit_id": commit_id}).mappings().all()
        return [dict(row) for row in rows]

    @staticmethod
    def get_version_history_by_file_version_id(db: Session, file_version_id: int) -> list[dict]:
        query = text(
            """
            with target as (
                select file_id
                from file_versions
                where id = :file_version_id
            )
            select
                fv.id as file_version_id,
                fv.version,
                fv.commit_id,
                fv.file_size,
                fv.is_deleted,
                fv.created_at
            from file_versions fv
            inner join target t on t.file_id = fv.file_id
            order by fv.version desc
            """
        )
        rows = db.execute(query, {"file_version_id": file_version_id}).mappings().all()
        return [dict(row) for row in rows]
