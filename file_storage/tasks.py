import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def run(cmd: list[str]) -> int:
    return subprocess.call(cmd, cwd=ROOT)


def main() -> int:
    parser = argparse.ArgumentParser(description="Task runner for file_storage")
    sub = parser.add_subparsers(dest="command", required=True)

    runserver = sub.add_parser("runserver", help="Run FastAPI dev server")
    runserver.add_argument("--host", default=os.getenv("FILE_STORAGE_API_HOST", "0.0.0.0"))
    runserver.add_argument("--port", default=os.getenv("FILE_STORAGE_API_PORT", "8080"))
    runserver.add_argument("--no-reload", action="store_true", help="Disable auto reload")

    migrate = sub.add_parser("migrate", help="Run DB migrations")
    migrate.add_argument("action", choices=["status", "up", "down"])
    migrate.add_argument("--steps", type=int, default=None)

    args = parser.parse_args()

    if args.command == "runserver":
        cmd = [sys.executable, "-m", "uvicorn", "app.main:app", "--host", str(args.host), "--port", str(args.port)]
        if not args.no_reload:
            cmd.append("--reload")
        return run(cmd)

    if args.command == "migrate":
        cmd = [sys.executable, "-m", "scripts.migrate", args.action]
        if args.steps is not None:
            cmd.extend(["--steps", str(args.steps)])
        return run(cmd)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
