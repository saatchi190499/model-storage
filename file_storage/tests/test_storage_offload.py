import tempfile
import unittest
from pathlib import Path

from app.api.routes.commit import _download_response
from app.storage.local_storage import LocalStorage


class StorageOffloadTests(unittest.TestCase):
    def test_accel_redirect_path_is_relative_to_storage_root_and_url_escaped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stored_file = root / "project one" / "commit-1" / "model file.json"
            stored_file.parent.mkdir(parents=True)
            stored_file.write_text("{}", encoding="utf-8")

            storage = LocalStorage(str(root))

            self.assertEqual(
                storage.get_accel_redirect_path(str(stored_file), "/internal-model-storage/"),
                "/internal-model-storage/project%20one/commit-1/model%20file.json",
            )

    def test_accel_redirect_path_rejects_storage_keys_outside_root(self) -> None:
        with tempfile.TemporaryDirectory() as storage_tmp, tempfile.TemporaryDirectory() as outside_tmp:
            outside_file = Path(outside_tmp) / "secret.txt"
            outside_file.write_text("secret", encoding="utf-8")
            storage = LocalStorage(storage_tmp)

            with self.assertRaises(ValueError):
                storage.get_accel_redirect_path(str(outside_file), "/internal-model-storage/")

    def test_download_response_can_handoff_to_nginx_after_authorization(self) -> None:
        response = _download_response(
            Path("ignored-by-nginx"),
            "models/model file.json",
            "/internal-model-storage/project/commit/model%20file.json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers["x-accel-redirect"],
            "/internal-model-storage/project/commit/model%20file.json",
        )
        self.assertIn("attachment;", response.headers["content-disposition"])
        self.assertIn("filename*=UTF-8''model%20file.json", response.headers["content-disposition"])
        self.assertEqual(response.headers["x-content-type-options"], "nosniff")

    def test_download_response_uses_ascii_fallback_for_non_ascii_filenames(self) -> None:
        response = _download_response(
            Path("ignored-by-nginx"),
            "models/\u0444\u0430\u0439\u043b.json",
            "/internal-model-storage/project/commit/%D1%84%D0%B0%D0%B9%D0%BB.json",
        )

        self.assertIn('filename=".json"', response.headers["content-disposition"])
        self.assertIn(
            "filename*=UTF-8''%D1%84%D0%B0%D0%B9%D0%BB.json",
            response.headers["content-disposition"],
        )


if __name__ == "__main__":
    unittest.main()
