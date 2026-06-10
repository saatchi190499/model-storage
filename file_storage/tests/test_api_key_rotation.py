import unittest

from fastapi import HTTPException
from starlette.requests import Request

from app.api.deps import require_api_key
from app.core.config import settings


def _request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/field/",
            "headers": [],
            "client": ("127.0.0.1", 12345),
            "server": ("model-storage", 8080),
            "scheme": "https",
            "query_string": b"",
        }
    )


class ApiKeyRotationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_api_key = settings.api_key
        self.original_previous_api_key = settings.previous_api_key

    def tearDown(self) -> None:
        settings.api_key = self.original_api_key
        settings.previous_api_key = self.original_previous_api_key

    def test_active_and_previous_keys_are_accepted_during_rotation(self) -> None:
        settings.api_key = "new-active-key"
        settings.previous_api_key = "old-previous-key"

        require_api_key(_request(), "new-active-key")
        require_api_key(_request(), "old-previous-key")

    def test_invalid_key_is_rejected(self) -> None:
        settings.api_key = "new-active-key"
        settings.previous_api_key = "old-previous-key"

        with self.assertRaises(HTTPException) as context:
            require_api_key(_request(), "invalid-key")

        self.assertEqual(context.exception.status_code, 401)

    def test_previous_key_cannot_replace_missing_active_key(self) -> None:
        settings.api_key = ""
        settings.previous_api_key = "old-previous-key"

        with self.assertRaises(HTTPException) as context:
            require_api_key(_request(), "old-previous-key")

        self.assertEqual(context.exception.status_code, 503)

    def test_duplicate_previous_key_does_not_enable_grace_state(self) -> None:
        settings.api_key = "same-key"
        settings.previous_api_key = " same-key "

        self.assertEqual(settings.accepted_api_keys, ("same-key",))


if __name__ == "__main__":
    unittest.main()
