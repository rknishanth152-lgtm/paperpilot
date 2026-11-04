"""FastAPI dependencies that build services. Tests override these."""

from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.database import get_sessionmaker
from app.services.ingestion.grobid import GrobidClient
from app.services.ingestion.pipeline import Ingestion
from app.storage import get_storage


def get_sessions() -> sessionmaker[Session]:
    return get_sessionmaker()


def get_ingestion() -> Ingestion:
    return Ingestion(
        get_sessionmaker(), get_storage(), GrobidClient.from_settings(get_settings())
    )
