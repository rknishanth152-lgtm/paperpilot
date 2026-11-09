"""FastAPI dependencies that build services. Tests override these."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings, get_settings
from app.database import get_sessionmaker
from app.services.answering.pipeline import Answering, AnswerLimits
from app.services.ingestion.grobid import GrobidClient
from app.services.ingestion.pipeline import Ingestion
from app.services.llm_factory import build_language_model
from app.services.reproducibility.assessment import Assessor, assessment_limits
from app.services.retrieval.selection import build_retriever
from app.storage import get_storage


def get_sessions() -> sessionmaker[Session]:
    return get_sessionmaker()


def get_ingestion() -> Ingestion:
    return Ingestion(
        get_sessionmaker(), get_storage(), GrobidClient.from_settings(get_settings())
    )


def get_assessor(settings: Annotated[Settings, Depends(get_settings)]) -> Assessor:
    sessions = get_sessionmaker()
    return Assessor(
        sessions,
        build_language_model(settings),
        assessment_limits(settings),
        build_retriever(settings, sessions),
    )


def get_answering(settings: Annotated[Settings, Depends(get_settings)]) -> Answering:
    sessions = get_sessionmaker()
    return Answering(
        sessions,
        build_language_model(settings),
        AnswerLimits.from_settings(settings),
        build_retriever(settings, sessions),
    )
