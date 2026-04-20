# Model Storage (FastAPI)

## Setup

```bash
cd file_storage
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
copy .env.example .env
```

## Run API

```bash
python tasks.py runserver
```

## Run With Docker

```bash
cd file_storage
docker compose up --build
```

API will be available at `http://localhost:8080`.
Docker compose expects an external PostgreSQL instance; set `FILE_STORAGE_DB_HOST`, `FILE_STORAGE_DB_PORT`, and credentials in `.env`.

## Migrations

```bash
python tasks.py migrate status
python tasks.py migrate up
python tasks.py migrate up --steps 1
python tasks.py migrate down --steps 1
```

## Notes

- SQL migrations are in `migrations/` and are executed by `scripts/migrate.py`.
- Migration state is tracked in the `schema_migrations` table.
- API routes mirror the original service paths.
- File blobs are stored on local disk under `FILE_STORAGE_STORAGE_DIR`.
