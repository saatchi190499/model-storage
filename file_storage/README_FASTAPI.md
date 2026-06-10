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

API will be available at `http://localhost:8080` for internal service-to-service calls only.
Docker compose expects an external PostgreSQL instance; set `FILE_STORAGE_DB_HOST`, `FILE_STORAGE_DB_PORT`, credentials, and `FILE_STORAGE_API_KEY` in `.env`.

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
- Production access mode is service-token-only. Direct browser/user access is not supported until a real user/project authorization model is added.
- API routes require `X-API-Key: <FILE_STORAGE_API_KEY>`. The service fails closed with HTTP 503 if the key is not configured, and denied attempts are logged without recording the supplied key.
- Safe rotation uses `FILE_STORAGE_PREVIOUS_API_KEY` only as a temporary grace credential. Set the new key as `FILE_STORAGE_API_KEY`, keep the old key as `FILE_STORAGE_PREVIOUS_API_KEY` while approved callers migrate, then remove the previous key after verification. The active key remains mandatory.
- The static browser UI and FastAPI docs are disabled by default with `FILE_STORAGE_ENABLE_UI=false` and `FILE_STORAGE_ENABLE_API_DOCS=false`. If either is enabled for troubleshooting, expose it only through an admin VPN/internal allowlist and disable it again after use.
- Keep model-storage on a private server/interface. Do not expose it directly to the internet or corporate LAN users; ProdCast should call it through the approved internal HTTPS URL with the service token.
- ZIP commits are bounded by `FILE_STORAGE_MAX_UPLOAD_BYTES`, `FILE_STORAGE_MAX_ZIP_FILES`, `FILE_STORAGE_MAX_ZIP_UNCOMPRESSED_BYTES`, and `FILE_STORAGE_MAX_ZIP_COMPRESSION_RATIO`. Unsafe paths such as absolute paths, drive-letter paths, `..`, and duplicate normalized entries are rejected.
- ZIP uploads are staged to a temporary file in `FILE_STORAGE_STREAM_CHUNK_BYTES` chunks instead of being loaded into memory. Project/commit ZIP downloads are generated as temporary files and streamed with `FileResponse`; temporary ZIPs are deleted after the response is sent.
