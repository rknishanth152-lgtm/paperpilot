"""Application entry point: `uvicorn app.main:app --app-dir backend`."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import health
from app.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Load settings at startup so missing or invalid configuration stops the
    # server immediately instead of failing on the first request.
    get_settings()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="PaperPilot", version="0.0.0", lifespan=lifespan)
    app.include_router(health.router)
    return app


app = create_app()
