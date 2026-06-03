import hashlib
import tempfile
import uuid
from pathlib import Path
from zipfile import BadZipFile, ZIP_DEFLATED, ZipFile

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.repositories.commit import CommitRepository
from app.storage.local_storage import LocalStorage


class CommitService:
    def __init__(self, db: Session, storage: LocalStorage) -> None:
        self.db = db
        self.storage = storage

    def process_zip_file(self, project_id: uuid.UUID, zip_path: Path, message: str, user_id: uuid.UUID) -> None:
        try:
            zip_obj = ZipFile(zip_path)
        except BadZipFile as exc:
            raise HTTPException(status_code=400, detail="Uploaded file must be a valid ZIP archive") from exc

        with zip_obj:
            self._process_zip_archive(project_id, zip_obj, message, user_id)

    def _process_zip_archive(self, project_id: uuid.UUID, zip_obj: ZipFile, message: str, user_id: uuid.UUID) -> None:
        file_map = self._normalized_zip_file_map(zip_obj)

        commit_id = CommitRepository.create_commit(self.db, project_id, user_id, message)

        files: list[dict] = []
        for normalized_path in file_map:
            file_path = Path(normalized_path)
            path = str(file_path.parent).replace("\\", "/")
            if path == ".":
                path = ""
            files.append(
                {
                    "project_id": project_id,
                    "name": file_path.stem,
                    "file_format": file_path.suffix,
                    "path": path,
                    "last_file_version": {
                        "file_size": file_map[normalized_path].file_size,
                        "commit_id": commit_id,
                    },
                }
            )

        existing_files = CommitRepository.get_files_by_project_id(self.db, project_id, active_only=True)
        existing_map = {self._join_file_path(f["path"], f"{f['name']}{f['file_format']}"): f for f in existing_files}

        changed_files: list[dict] = []
        renamed_files: list[dict] = []
        new_files: list[dict] = []
        deleted_files: list[dict] = []
        matched_existing_paths: set[str] = set()
        matched_uploaded_paths: set[str] = set()
        uploaded_by_path: dict[str, dict] = {}

        for file in files:
            full_path = self._join_file_path(file["path"], f"{file['name']}{file['file_format']}")
            zf = file_map.get(full_path)
            if zf is None:
                continue
            with zip_obj.open(zf) as handle:
                file_hash = self._calculate_file_hash(handle)

            file["last_file_version"]["hash"] = file_hash
            file["last_file_version"]["is_deleted"] = False
            uploaded_by_path[full_path] = file

            existing = existing_map.get(full_path)
            if existing is None:
                continue

            matched_existing_paths.add(full_path)
            matched_uploaded_paths.add(full_path)

            if file_hash != existing["hash"]:
                file["id"] = existing["file_id"]
                changed_files.append(file)

        unmatched_existing = {k: v for k, v in existing_map.items() if k not in matched_existing_paths}
        unmatched_uploaded = {k: v for k, v in uploaded_by_path.items() if k not in matched_uploaded_paths}

        existing_by_hash: dict[str, list[dict]] = {}
        for existing in unmatched_existing.values():
            existing_by_hash.setdefault(existing["hash"], []).append(existing)

        consumed_existing_ids: set[int] = set()
        for uploaded in unmatched_uploaded.values():
            candidates = existing_by_hash.get(uploaded["last_file_version"]["hash"], [])
            if candidates:
                existing = candidates.pop(0)
                uploaded["id"] = existing["file_id"]
                renamed_files.append(uploaded)
                consumed_existing_ids.add(existing["file_id"])
            else:
                new_files.append(uploaded)

        for existing in unmatched_existing.values():
            if existing["file_id"] in consumed_existing_ids:
                continue
            deleted_files.append(
                {
                    "id": existing["file_id"],
                    "project_id": existing["project_id"],
                    "name": existing["name"],
                    "file_format": existing["file_format"],
                    "path": existing["path"],
                    "last_file_version": {
                        "is_deleted": True,
                        "commit_id": commit_id,
                        "file_size": 0,
                        "hash": "",
                    },
                }
            )

        if changed_files or renamed_files or new_files or deleted_files:
            self._commit_files(changed_files + renamed_files, new_files, deleted_files, zip_obj)
            self.db.commit()
        else:
            CommitRepository.delete_commit(self.db, commit_id)
            self.db.commit()

    def create_project_archive(self, project_id: uuid.UUID) -> Path:
        files = CommitRepository.get_files_by_project_id(self.db, project_id, active_only=True)
        return self._build_zip_file(files)

    def create_commit_archive(self, commit_id: int) -> Path:
        files = CommitRepository.get_files_at_commit(self.db, commit_id)
        return self._build_zip_file(files)

    def get_commits_by_project_id(self, project_id: uuid.UUID) -> list[dict]:
        return CommitRepository.get_commits_by_project_id(self.db, project_id)

    def list_project_file_paths(self, project_id: uuid.UUID) -> list[str]:
        files = CommitRepository.get_files_by_project_id(self.db, project_id, active_only=True)
        out: list[str] = []
        for file in files:
            if not file.get("storage_key"):
                continue
            full_path = self._join_file_path(file["path"], f"{file['name']}{file['file_format']}")
            normalized = self._normalize_relative_path(full_path)
            if normalized:
                out.append(normalized)
        return sorted(dict.fromkeys(out))

    def get_project_file_path(self, project_id: uuid.UUID, path: str) -> tuple[Path, str]:
        requested = self._normalize_relative_path(path)
        if not requested:
            raise HTTPException(status_code=400, detail="path is required")

        files = CommitRepository.get_files_by_project_id(self.db, project_id, active_only=True)
        for file in files:
            full_path = self._join_file_path(file["path"], f"{file['name']}{file['file_format']}")
            if self._normalize_relative_path(full_path) != requested:
                continue

            storage_key = file.get("storage_key")
            if not storage_key:
                break

            try:
                return self.storage.get_file_path(storage_key), requested
            except FileNotFoundError as exc:
                raise HTTPException(status_code=404, detail=f"file not found: {requested}") from exc

        raise HTTPException(status_code=404, detail=f"file not found: {requested}")

    def _commit_files(self, changed_files: list[dict], new_files: list[dict], deleted_files: list[dict], zip_obj: ZipFile) -> None:
        file_versions = CommitRepository.commit_files(self.db, changed_files, new_files, deleted_files)
        stored = self.storage.save_files(file_versions, zip_obj)
        CommitRepository.update_file_versions(self.db, stored)

        if changed_files:
            project_id = changed_files[0]["project_id"]
            commit_id = changed_files[0]["last_file_version"]["commit_id"]
        elif new_files:
            project_id = new_files[0]["project_id"]
            commit_id = new_files[0]["last_file_version"]["commit_id"]
        else:
            project_id = deleted_files[0]["project_id"]
            commit_id = deleted_files[0]["last_file_version"]["commit_id"]

        CommitRepository.update_commit(self.db, project_id, commit_id)

    def _build_zip_file(self, files: list[dict]) -> Path:
        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
                temp_path = Path(tmp.name)

            with ZipFile(temp_path, "w", compression=ZIP_DEFLATED) as archive:
                self._write_files_to_archive(archive, files)

            return temp_path
        except Exception:
            if temp_path and temp_path.exists():
                temp_path.unlink(missing_ok=True)
            raise

    def _write_files_to_archive(self, archive: ZipFile, files: list[dict]) -> None:
        for file in files:
            storage_key = file.get("storage_key")
            if not storage_key:
                continue
            zip_path = self._join_file_path(file["path"], f"{file['name']}{file['file_format']}")
            normalized = self._normalize_relative_path(zip_path)
            if not normalized:
                continue
            try:
                storage_path = self.storage.get_file_path(storage_key)
            except FileNotFoundError as exc:
                raise HTTPException(status_code=404, detail=f"stored file missing: {normalized}") from exc
            archive.write(storage_path, arcname=normalized)

    @staticmethod
    def _join_file_path(path: str, filename: str) -> str:
        if not path or path == ".":
            return filename
        return f"{path.strip('/')}/{filename}".replace("\\", "/")

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
    def _calculate_file_hash(handle) -> str:
        digest = hashlib.sha256()
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _normalized_zip_file_map(zip_obj: ZipFile) -> dict[str, object]:
        entries = [item for item in zip_obj.infolist() if not item.is_dir()]
        if not entries:
            raise HTTPException(status_code=400, detail="ZIP archive does not contain files")
        if len(entries) > settings.max_zip_files:
            raise HTTPException(status_code=413, detail=f"ZIP contains more than {settings.max_zip_files} files")

        total_uncompressed = sum(max(0, int(item.file_size or 0)) for item in entries)
        if total_uncompressed > settings.max_zip_uncompressed_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"ZIP uncompressed size exceeds {settings.max_zip_uncompressed_bytes} bytes",
            )

        for item in entries:
            compressed_size = max(1, int(item.compress_size or 1))
            if item.file_size / compressed_size > settings.max_zip_compression_ratio:
                raise HTTPException(status_code=400, detail=f"Suspicious ZIP compression ratio for {item.filename}")

        raw_paths = [item.filename.replace("\\", "/").lstrip("/") for item in entries]

        top_level_parts = [path.split("/", 1)[0] for path in raw_paths if "/" in path]
        has_root_files = any("/" not in path for path in raw_paths)
        strip_prefix = ""

        if raw_paths and not has_root_files and top_level_parts:
            common_top = top_level_parts[0]
            if all(path.startswith(common_top + "/") for path in raw_paths):
                strip_prefix = common_top + "/"

        normalized: dict[str, object] = {}
        for item in entries:
            raw_original = item.filename.replace("\\", "/")
            if raw_original.startswith("/") or ":" in raw_original:
                raise HTTPException(status_code=400, detail=f"Unsafe ZIP path: {item.filename}")
            raw = raw_original.lstrip("/")
            clean = raw[len(strip_prefix):] if strip_prefix and raw.startswith(strip_prefix) else raw
            clean = CommitService._normalize_relative_path(clean)
            if not clean:
                raise HTTPException(status_code=400, detail=f"Unsafe ZIP path: {item.filename}")
            if clean in normalized:
                raise HTTPException(status_code=400, detail=f"Duplicate ZIP path: {clean}")
            normalized[clean] = item
        return normalized
