"""FastAPI dependencies that build services. Tests override these."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings, get_settings
from app.database import get_sessionmaker
from app.services.answering.pipeline import Answering, AnswerLimits
from app.services.ingestion.grobid import GrobidClient
from app.services.ingestion.pipeline import Ingestion
from app.services.llm_anthropic import build_language_model
from app.storage import get_storage


def get_sessions() -> sessionmaker[Session]:
    return get_sessionmaker()


def get_ingestion() -> Ingestion:
    return Ingestion(
        get_sessionmaker(), get_storage(), GrobidClient.from_settings(get_settings())
    )


def get_answering(settings: Annotated[Settings, Depends(get_settings)]) -> Answering:
    return Answering(
        get_sessionmaker(),
        build_language_model(settings),
        AnswerLimits.from_settings(settings),
    )
