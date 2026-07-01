from __future__ import annotations

import logging
import re

_REDACTED = "***REDACTED***"
_KEY_VALUE_PATTERN = re.compile(
    r"(?i)\b(authorization|x-api-key|api[_-]?key|access[_-]?token|refresh[_-]?token|"
    r"id[_-]?token|client[_-]?secret|secret[_-]?key|password|passwd|pwd|token|secret)"
    r"(\s*[:=]\s*)(['\"]?)([^'\"\s,;{}]+)(['\"]?)"
)
_BEARER_PATTERN = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+")
_BASIC_PATTERN = re.compile(r"(?i)\bBasic\s+[A-Za-z0-9._~+/=-]+")
_URL_CREDENTIAL_PATTERN = re.compile(r"(?P<scheme>[A-Za-z][A-Za-z0-9+.-]*://)(?P<user>[^:/@\s]+):(?P<password>[^@\s]+)@")
_INSTALLED = False


def redact_secrets(value) -> str:
    text = str(value)
    text = _BEARER_PATTERN.sub("Bearer " + _REDACTED, text)
    text = _BASIC_PATTERN.sub("Basic " + _REDACTED, text)
    text = _URL_CREDENTIAL_PATTERN.sub(r"\g<scheme>\g<user>:" + _REDACTED + "@", text)
    return _KEY_VALUE_PATTERN.sub(
        lambda match: f"{match.group(1)}{match.group(2)}{match.group(3)}{_REDACTED}{match.group(5)}",
        text,
    )


def install_log_redaction() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    previous_factory = logging.getLogRecordFactory()

    def redacting_factory(*args, **kwargs):
        record = previous_factory(*args, **kwargs)
        record.msg = redact_secrets(record.getMessage())
        record.args = ()
        return record

    logging.setLogRecordFactory(redacting_factory)
    _INSTALLED = True


__all__ = ["install_log_redaction", "redact_secrets"]
