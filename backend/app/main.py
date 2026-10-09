from contextlib import asynccontextmanager
import logging

from pathlib import Path

import sentry_sdk
from fastapi import FastAPI
from fastapi.routing import APIRoute
from starlette.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles
from starlette.exceptions import HTTPException
from starlette.concurrency import run_in_threadpool

from app.api.main import api_router
from app.api.routes.health import router as health_router
from app.core.config import settings

FRONTEND_DIR = Path(__file__).parent / "frontend"


def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}" if route.tags else route.name


if settings.SENTRY_DSN and settings.FASTAPI_ENV != "development":
    sentry_sdk.init(dsn=str(settings.SENTRY_DSN), enable_tracing=True)

@asynccontextmanager
async def lifespan(app):
    from app.core.jobs import recover_interrupted_jobs
    try:
        if not getattr(app.state, "jobs_recovered", False):
            await run_in_threadpool(recover_interrupted_jobs)
            app.state.jobs_recovered = True
    except Exception:
        logging.getLogger("tathya.startup").exception("Job recovery unavailable")
    yield


app = FastAPI(
    lifespan=lifespan,
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    generate_unique_id_function=custom_generate_unique_id,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(dict.fromkeys([settings.FRONTEND_HOST, "http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:4173", "http://127.0.0.1:4173", "https://localhost", "capacitor://localhost"])),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(health_router)  # root: /health, /demo/readiness

class FrontendFiles(StaticFiles):
    async def get_response(self, path, scope):
        path = path.replace("\\", "/").lstrip("/")
        if path == "api" or path.startswith("api/"):
            raise HTTPException(status_code=404)
        try:
            return await super().get_response(path, scope)
        except HTTPException as exc:
            # Only page navigation falls back to the application shell.
            headers = dict(scope.get("headers", []))
            if exc.status_code == 404 and b"text/html" in headers.get(b"accept", b"") and "." not in path.rsplit("/", 1)[-1]:
                return await super().get_response("index.html", scope)
            raise


if (FRONTEND_DIR / "index.html").exists():
    app.mount("/", FrontendFiles(directory=FRONTEND_DIR, html=True), name="frontend")
