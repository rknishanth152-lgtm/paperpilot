"""The embedding interface, its validation and its fake (R2; FR-RET-005, AD-011)."""

import math

import pytest

from app.services.embeddings import (
    DocumentText,
    Embedder,
    EmbeddingDimensionError,
    EmbeddingMalformedError,
    FakeEmbedder,
    validated_vectors,
)
from app.services.llm import ModelRateLimitError

DOC = DocumentText(title="Ice", text="Glaciers retreated.")


def test_the_fake_satisfies_the_interface() -> None:
    embedder: Embedder = FakeEmbedder(dimensions=4)

    assert embedder.model_name == "fake-embedding"
    assert embedder.dimensions == 4
    assert embedder.text_format == "fake-v1"


def test_the_fake_is_deterministic_and_depends_on_the_text() -> None:
    other = DocumentText(title="Ice", text="Rocks moved.")

    first = FakeEmbedder(dimensions=4).embed_documents([DOC, other])
    second = FakeEmbedder(dimensions=4).embed_documents([DOC, other])

    assert first == second
    assert first[0] != first[1]
    assert all(len(vector) == 4 for vector in first)


def test_the_fake_records_calls_and_answers_queries() -> None:
    embedder = FakeEmbedder(dimensions=4)

    embedder.embed_documents([DOC])
    vector = embedder.embed_query("Why?")

    assert embedder.document_calls == [[DOC]]
    assert embedder.query_calls == ["Why?"]
    assert len(vector) == 4


def test_the_fake_raises_a_scripted_failure_on_the_chosen_call() -> None:
    embedder = FakeEmbedder(dimensions=4, failures={2: ModelRateLimitError()})

    embedder.embed_documents([DOC])
    with pytest.raises(ModelRateLimitError):
        embedder.embed_documents([DOC])
    embedder.embed_documents([DOC])


def test_the_fake_can_be_given_chosen_vectors() -> None:
    embedder = FakeEmbedder(dimensions=2, vectors={"Why?": [1.0, 0.0]})

    assert embedder.embed_query("Why?") == [1.0, 0.0]
    assert embedder.embed_documents([DocumentText(None, "Why?")]) == [[1.0, 0.0]]


def test_valid_vectors_are_returned_as_floats() -> None:
    assert validated_vectors([[1, 0.5], [0, 2]], count=2, dimensions=2) == [
        [1.0, 0.5],
        [0.0, 2.0],
    ]


@pytest.mark.parametrize(
    ("vectors", "count", "error"),
    [
        pytest.param([[1.0, 0.0]], 2, EmbeddingMalformedError, id="too few"),
        pytest.param([[1.0, 0.0]] * 3, 2, EmbeddingMalformedError, id="too many"),
        pytest.param([[1.0, 0.0, 0.0]], 1, EmbeddingDimensionError, id="too long"),
        pytest.param([[1.0]], 1, EmbeddingDimensionError, id="too short"),
        pytest.param([[math.nan, 1.0]], 1, EmbeddingMalformedError, id="nan"),
        pytest.param([[math.inf, 1.0]], 1, EmbeddingMalformedError, id="infinite"),
        pytest.param([[0.0, 0.0]], 1, EmbeddingMalformedError, id="zero vector"),
    ],
)
def test_an_unusable_response_is_refused(
    vectors: list[list[float]], count: int, error: type[Exception]
) -> None:
    with pytest.raises(error):
        validated_vectors(vectors, count=count, dimensions=2)


def test_the_later_vector_is_checked_too() -> None:
    with pytest.raises(EmbeddingDimensionError):
        validated_vectors([[1.0, 0.0], [1.0]], count=2, dimensions=2)
