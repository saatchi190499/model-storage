#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


MAX_FILE_BYTES = 2 * 1024 * 1024
SKIP_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".pdf",
    ".zip",
    ".gz",
    ".7z",
    ".lock",
}
SKIP_NAMES = {
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
}

HIGH_CONFIDENCE_PATTERNS = [
    ("private-key", re.compile(r"-----BEGIN (?:RSA |DSA |EC |OPENSSH |PGP )?PRIVATE KEY-----")),
    ("aws-access-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("github-token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{36,}\b")),
    ("slack-token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b")),
    ("openai-token", re.compile(r"\bsk-[A-Za-z0-9]{32,}\b")),
]

GENERIC_QUOTED_ASSIGNMENT = re.compile(
    r"(?i)\b("
    r"password|passwd|pwd|secret|secret_key|client_secret|api_key|apikey|token|"
    r"access_token|refresh_token|private_key|license_service_token"
    r")\b\s*[:=]\s*(['\"])([^'\"]+)\2"
)
GENERIC_ENV_ASSIGNMENT = re.compile(
    r"(?i)^("
    r"[A-Z0-9_]*(?:PASSWORD|PASSWD|PWD|SECRET|SECRET_KEY|CLIENT_SECRET|API_KEY|APIKEY|TOKEN|"
    r"ACCESS_TOKEN|REFRESH_TOKEN|PRIVATE_KEY|LICENSE_SERVICE_TOKEN)[A-Z0-9_]*"
    r")\s*=\s*([^#\s]+)"
)

ALLOW_VALUE_PARTS = {
    "",
    "none",
    "null",
    "false",
    "true",
    "dummy",
    "example",
    "placeholder",
    "changeme",
    "change-this",
    "change-this-salt",
    "secret-key",
    "supersecret",
    "password",
    "postgres",
    "license_app",
}


def _repo_files(repo: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=repo,
        text=True,
        check=True,
        capture_output=True,
    )
    return [repo / line.strip() for line in result.stdout.splitlines() if line.strip()]


def _is_binary(path: Path) -> bool:
    try:
        chunk = path.read_bytes()[:4096]
    except OSError:
        return True
    return b"\0" in chunk


def _should_skip(path: Path) -> bool:
    if path.name in SKIP_NAMES:
        return True
    if path.suffix.lower() in SKIP_SUFFIXES:
        return True
    parts = {part.lower() for part in path.parts}
    return bool(parts.intersection({"node_modules", ".git", "__pycache__", "dist", "build", "staticfiles"}))


def _looks_like_placeholder(value: str) -> bool:
    normalized = value.strip().strip("'\"").strip()
    lowered = normalized.lower()
    if lowered in ALLOW_VALUE_PARTS:
        return True
    if lowered.startswith(("<", "${", "$", "env(", "os.getenv(")):
        return True
    if any(char in normalized for char in ("(", "{", "[")):
        return True
    if any(marker in lowered for marker in ("example", "placeholder", "replace-me", "set-", "your-", "dummy")):
        return True
    if len(normalized) < 16:
        return True
    return False


def _env_like_file(path: Path) -> bool:
    name = path.name.lower()
    return (
        name.startswith(".env")
        or name.endswith(".env")
        or path.suffix.lower() in {".env", ".ini", ".cfg", ".conf", ".properties"}
    )


def scan_file(path: Path, repo: Path) -> list[str]:
    if _should_skip(path) or not path.is_file() or path.stat().st_size > MAX_FILE_BYTES or _is_binary(path):
        return []
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []

    findings: list[str] = []
    rel = path.relative_to(repo)
    for name, pattern in HIGH_CONFIDENCE_PATTERNS:
        for match in pattern.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            findings.append(f"{rel}:{line}: {name}")

    env_like = _env_like_file(path)
    for idx, line_text in enumerate(text.splitlines(), start=1):
        stripped = line_text.strip()
        if not stripped or stripped.startswith(("#", "//", "/*", "*")):
            continue
        match = GENERIC_ENV_ASSIGNMENT.search(stripped) if env_like else GENERIC_QUOTED_ASSIGNMENT.search(stripped)
        if not match:
            continue
        value = match.group(2 if env_like else 3).rstrip(",;")
        if not _looks_like_placeholder(value):
            findings.append(f"{rel}:{idx}: generic-secret-assignment ({match.group(1)})")

    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan tracked source files for committed secrets.")
    parser.add_argument("--repo", default=".", help="Repository root to scan.")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    findings: list[str] = []
    for path in _repo_files(repo):
        findings.extend(scan_file(path, repo))

    if findings:
        print("Potential committed secrets found:", file=sys.stderr)
        for finding in findings:
            print(f"  {finding}", file=sys.stderr)
        return 1
    print("Secret scan passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
