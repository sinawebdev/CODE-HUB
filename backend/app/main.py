from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1 import api_router
from app.core.config import settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging

configure_logging()
if not settings.is_development and settings.secret_key in ("", "change-me"):
    raise RuntimeError("Set SECRET_KEY to a long random value before running outside development.")

app = FastAPI(title=settings.app_name, version=settings.app_version)
register_exception_handlers(app)
if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=False,
        allow_methods=["*"], allow_headers=["Authorization", "Content-Type"],
    )
app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


# The frontend is plain static files; serve it from the same origin in development.
# Mounted last so /api/v1, /health and /docs keep priority.
if settings.serve_frontend and settings.frontend_dir.is_dir():
    app.mount("/", StaticFiles(directory=settings.frontend_dir, html=True), name="frontend")
