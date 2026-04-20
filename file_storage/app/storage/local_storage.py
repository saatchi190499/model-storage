import os
import shutil
from pathlib import Path
from zipfile import ZipFile


class LocalStorage:
    def __init__(self, base_dir: str) -> None:
        self.base_dir = Path(base_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def get_file(self, storage_key: str) -> bytes:
        path = Path(storage_key)
        if not path.exists():
            raise FileNotFoundError(f"file {storage_key} not found")
        return path.read_bytes()

    def delete_files(self, storage_keys: list[str]) -> None:
        for key in storage_keys:
            if not key:
                continue
            path = Path(key)
            try:
                if path.exists() and path.is_file():
                    path.unlink()
            except OSError:
                continue

    def delete_project_tree(self, project_id: str) -> None:
        project_dir = self.base_dir / str(project_id)
        if project_dir.exists() and project_dir.is_dir():
            shutil.rmtree(project_dir, ignore_errors=True)

    def save_files(self, files: list[dict], zip_file: ZipFile) -> list[dict]:
        zip_entries_by_normalized_path = self._normalized_zip_entries(zip_file)

        for idx, file in enumerate(files):
            if file.get("is_deleted"):
                continue

            commit_dir = self.base_dir / str(file["project_id"]) / str(file["commit_id"])
            commit_dir.mkdir(parents=True, exist_ok=True)

            filename = f"{file['name']}{file['file_format']}"
            local_path = commit_dir / filename
            dup_index = 1
            while local_path.exists():
                dup_dir = commit_dir / f"dup{dup_index}"
                dup_dir.mkdir(parents=True, exist_ok=True)
                local_path = dup_dir / filename
                dup_index += 1

            full_path = str(Path(file["path"]) / filename).replace("\\", "/")
            entry = zip_entries_by_normalized_path.get(full_path)
            if entry is None:
                raise KeyError(f"ZIP entry not found for normalized path '{full_path}'")

            with zip_file.open(entry) as source:
                local_path.write_bytes(source.read())

            files[idx]["storage_key"] = str(local_path)

        return files

    @staticmethod
    def _normalized_zip_entries(zip_file: ZipFile) -> dict[str, object]:
        entries = [item for item in zip_file.infolist() if not item.is_dir()]
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
            raw = item.filename.replace("\\", "/").lstrip("/")
            clean = raw[len(strip_prefix):] if strip_prefix and raw.startswith(strip_prefix) else raw
            normalized[clean] = item
        return normalized
