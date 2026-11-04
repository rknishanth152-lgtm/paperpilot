"""Application entry point: `uvicorn app.main:app --app-dir backend`.

Run a single server process (uvicorn's default): startup recovery assumes no
other process is ingesting at the same time (AD-010).
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import documents, health
from app.api.errors import install_error_handlers
from app.config import get_settings
from app.database import get_sessionmaker
from app.services.ingestion.recovery import recover_interrupted


def recover_on_startup() -> None:
    """Documents left `processing` by a crash become `failed`/`interrupted` (FR-ING-010)."""
    recover_interrupted(get_sessionmaker())


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Load settings at startup so missing or invalid configuration stops the
    # server immediately instead of failing on the first request.
    get_settings()
    # Fails startup if the database is unreachable: never run with documents
    # stuck in `processing`.
    recover_on_startup()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="PaperPilot", version="0.0.0", lifespan=lifespan)
    install_error_handlers(app)
    app.include_router(health.router)
    app.include_router(documents.router)
    return app


app = create_app()
