from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.api.routes.commit import router as commit_router
from app.api.routes.field import router as field_router
from app.api.routes.file import router as file_router
from app.api.routes.project import router as project_router
from app.api.deps import require_api_key
from app.core.config import settings
from app.core.log_redaction import install_log_redaction
from app.db.session import engine

install_log_redaction()

app = FastAPI(
    title=settings.app_name,
    docs_url="/docs" if settings.enable_api_docs else None,
    redoc_url="/redoc" if settings.enable_api_docs else None,
    openapi_url="/openapi.json" if settings.enable_api_docs else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key"],
)


static_dir = Path(__file__).parent / "static"
if settings.enable_ui:
    app.mount("/ui", StaticFiles(directory=static_dir, html=True), name="ui")


@app.get("/")
async def root_redirect() -> RedirectResponse | JSONResponse:
    if settings.enable_ui:
        return RedirectResponse(url="/ui")
    return JSONResponse(
        status_code=404,
        content={"message": "Model-storage browser UI is disabled. Use the internal service API."},
    )


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "model-storage"}


@app.get("/readyz")
async def readyz() -> JSONResponse:
    checks: dict[str, object] = {}
    ok = True

    if settings.api_key:
        checks["api_key"] = "ok"
    else:
        checks["api_key"] = "missing"
        ok = False

    checks["ui"] = "enabled" if settings.enable_ui else "disabled"
    checks["api_docs"] = "enabled" if settings.enable_api_docs else "disabled"

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error: {exc.__class__.__name__}"
        ok = False

    try:
        storage_dir = Path(settings.storage_dir)
        storage_dir.mkdir(parents=True, exist_ok=True)
        test_path = storage_dir / ".readyz"
        test_path.write_text("ok", encoding="utf-8")
        test_path.unlink(missing_ok=True)
        checks["storage_dir"] = "ok"
    except Exception as exc:
        checks["storage_dir"] = f"error: {exc.__class__.__name__}"
        ok = False

    return JSONResponse(
        status_code=200 if ok else 503,
        content={"status": "ok" if ok else "degraded", "service": "model-storage", "checks": checks},
    )


@app.exception_handler(404)
async def not_found_handler(_request: Request, _exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=404, content={"message": "Page not found"})


api_auth = [Depends(require_api_key)]
app.include_router(commit_router, dependencies=api_auth)
app.include_router(field_router, dependencies=api_auth)
app.include_router(file_router, dependencies=api_auth)
app.include_router(project_router, dependencies=api_auth)

