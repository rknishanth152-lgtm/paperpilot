"""Loading the passages shown to the labeller (P6-T3)."""

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from tests.evaluation.claim_support import ShownPassage, load_passages
from tests.integration.test_keyword_retrieval import add_document

from app.models import Passage


def only_passage(sessions: sessionmaker[Session], document_id: uuid.UUID) -> uuid.UUID:
    with sessions() as session:
        return session.scalars(
            select(Passage.id).where(Passage.document_id == document_id)
        ).one()


def test_passages_come_back_with_their_stored_location(
    sessions: sessionmaker[Session],
) -> None:
    document = add_document(
        sessions,
        {
            "text": "The glaciers retreated.",
            "section_title": "Methods",
            "page_start": 3,
            "page_end": 3,
        },
    )
    passage = only_passage(sessions, document)

    loaded = load_passages(sessions, [passage])

    assert set(loaded) == {passage}
    assert loaded[passage] == ShownPassage("The glaciers retreated.", "Methods", 3)


def test_a_passage_that_no_longer_exists_stops_the_load(
    sessions: sessionmaker[Session],
) -> None:
    missing = uuid.uuid4()

    with pytest.raises(LookupError, match=str(missing)):
        load_passages(sessions, [missing])
