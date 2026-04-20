from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes.commit import router as commit_router
from app.api.routes.field import router as field_router
from app.api.routes.file import router as file_router
from app.api.routes.project import router as project_router
from app.core.config import settings

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


static_dir = Path(__file__).parent / "static"
app.mount("/ui", StaticFiles(directory=static_dir, html=True), name="ui")


@app.get("/")
async def root_redirect() -> RedirectResponse:
    return RedirectResponse(url="/ui")


@app.exception_handler(404)
async def not_found_handler(_request: Request, _exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=404, content={"message": "Page not found"})


app.include_router(commit_router)
app.include_router(field_router)
app.include_router(file_router)
app.include_router(project_router)

