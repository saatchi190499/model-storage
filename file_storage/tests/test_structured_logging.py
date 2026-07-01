import json
import logging
import unittest

from app.core.structured_logging import JsonLogFormatter


class StructuredLoggingTests(unittest.TestCase):
    def test_json_formatter_preserves_indexed_fields_and_redacts_secrets(self) -> None:
        record = logging.LogRecord(
            "model_storage.auth",
            logging.WARNING,
            __file__,
            10,
            "denied api_key=secret-value",
            (),
            None,
        )
        record.event = "model_storage.auth.denied"
        record.path = "/project-files/example"
        record.method = "GET"
        record.client = "127.0.0.1"
        record.has_key = True
        record.authorization = "Bearer secret-token"

        payload = json.loads(JsonLogFormatter().format(record))

        self.assertEqual(payload["service"], "model-storage")
        self.assertEqual(payload["event"], "model_storage.auth.denied")
        self.assertEqual(payload["path"], "/project-files/example")
        self.assertEqual(payload["method"], "GET")
        self.assertEqual(payload["client"], "127.0.0.1")
        self.assertTrue(payload["has_key"])
        self.assertNotIn("secret-value", payload["message"])
        self.assertNotIn("secret-token", payload["authorization"])


if __name__ == "__main__":
    unittest.main()
