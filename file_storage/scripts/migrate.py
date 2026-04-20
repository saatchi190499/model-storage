import argparse
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor

ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS_DIR = ROOT / "migrations"


@dataclass
class Migration:
    name: str
    up_sql: str
    down_sql: str


def load_env_file() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return

    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def db_config() -> dict[str, str | int]:
    return {
        "host": os.getenv("FILE_STORAGE_DB_HOST", "localhost"),
        "port": int(os.getenv("FILE_STORAGE_DB_PORT", "5432")),
        "user": os.getenv("FILE_STORAGE_DB_USER", "postgres"),
        "password": os.getenv("FILE_STORAGE_DB_PASSWORD", "postgres"),
        "dbname": os.getenv("FILE_STORAGE_DB_NAME", "file-storage"),
        "sslmode": os.getenv("FILE_STORAGE_DB_SSL_MODE", "disable"),
    }


def parse_section(sql: str, marker: str) -> str:
    pattern = re.compile(
        rf"--\s*\+goose\s+{marker}\s*\n"
        r"--\s*\+goose\s+StatementBegin\s*\n"
        r"(?P<body>.*?)"
        r"--\s*\+goose\s+StatementEnd",
        re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(sql)
    if not match:
        return ""
    body = match.group("body")
    lines = [line for line in body.splitlines() if line.strip() and not line.strip().lower().startswith("select 'up sql query'") and not line.strip().lower().startswith("select 'down sql query'")]
    return "\n".join(lines).strip()


def load_migrations() -> list[Migration]:
    migrations: list[Migration] = []
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        sql = path.read_text(encoding="utf-8")
        up_sql = parse_section(sql, "Up")
        down_sql = parse_section(sql, "Down")
        migrations.append(Migration(name=path.name, up_sql=up_sql, down_sql=down_sql))
    return migrations


def ensure_table(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            create table if not exists schema_migrations (
                filename text primary key,
                applied_at timestamptz not null default now()
            )
            """
        )
    conn.commit()


def applied_set(conn) -> set[str]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("select filename from schema_migrations")
        rows = cur.fetchall()
    return {row["filename"] for row in rows}


def last_applied(conn, count: int) -> list[str]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            select filename
            from schema_migrations
            order by applied_at desc, filename desc
            limit %s
            """,
            (count,),
        )
        rows = cur.fetchall()
    return [row["filename"] for row in rows]


def exec_sql(conn, sql: str) -> None:
    if not sql.strip():
        return
    with conn.cursor() as cur:
        cur.execute(sql)


def status(conn) -> int:
    ensure_table(conn)
    applied = applied_set(conn)
    migrations = load_migrations()

    for migration in migrations:
        state = "APPLIED" if migration.name in applied else "PENDING"
        print(f"{state:8} {migration.name}")
    return 0


def up(conn, steps: int | None) -> int:
    ensure_table(conn)
    applied = applied_set(conn)
    pending = [m for m in load_migrations() if m.name not in applied]
    if steps is not None:
        pending = pending[:steps]

    if not pending:
        print("No pending migrations.")
        return 0

    for migration in pending:
        try:
            exec_sql(conn, migration.up_sql)
            with conn.cursor() as cur:
                cur.execute(
                    "insert into schema_migrations (filename, applied_at) values (%s, %s)",
                    (migration.name, datetime.now(timezone.utc)),
                )
            conn.commit()
            print(f"APPLIED  {migration.name}")
        except Exception:
            conn.rollback()
            raise
    return 0


def down(conn, steps: int) -> int:
    ensure_table(conn)
    applied_recent = last_applied(conn, steps)
    if not applied_recent:
        print("No applied migrations to rollback.")
        return 0

    by_name = {m.name: m for m in load_migrations()}
    for name in applied_recent:
        migration = by_name.get(name)
        if migration is None:
            raise RuntimeError(f"migration file not found for applied record: {name}")
        try:
            exec_sql(conn, migration.down_sql)
            with conn.cursor() as cur:
                cur.execute("delete from schema_migrations where filename = %s", (name,))
            conn.commit()
            print(f"ROLLED   {name}")
        except Exception:
            conn.rollback()
            raise
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Migration runner for file_storage")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="Show migration status")

    up_parser = sub.add_parser("up", help="Apply pending migrations")
    up_parser.add_argument("--steps", type=int, default=None, help="Apply only N pending migrations")

    down_parser = sub.add_parser("down", help="Rollback applied migrations")
    down_parser.add_argument("--steps", type=int, default=1, help="Rollback N migrations")

    return parser


def main() -> int:
    load_env_file()
    args = build_parser().parse_args()

    with psycopg2.connect(**db_config()) as conn:
        if args.command == "status":
            return status(conn)
        if args.command == "up":
            return up(conn, args.steps)
        if args.command == "down":
            return down(conn, args.steps)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
