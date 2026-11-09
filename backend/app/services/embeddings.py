"""The one interface to embedding models, and a fake for tests (R2).

FR-RET-005, AD-011. Retrieval depends on `Embedder`, never on a provider.
Failures use the same `ModelError` family as language models, so a failure can
never turn into a stored or searched vector.

Provider responses are untrusted: `validated_vectors` checks each one.
"""

import hashlib
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

from app.services.llm import ModelError


class EmbeddingNotConfiguredError(ModelError):
    code = "embedding_not_configured"
    message = "No embedding model is configured."


class EmbeddingDimensionError(ModelError):
    code = "embedding_dimension_mismatch"
    message = "The embedding has a different size from the one expected."


class EmbeddingMalformedError(ModelError):
    code = "embedding_malformed"
    message = "The embedding model returned an unusable response."


@dataclass(frozen=True)
class DocumentText:
    """A passage to embed. A missing title stays None."""

    title: str | None
    text: str


class Embedder(Protocol):
    @property
    def model_name(self) -> str: ...

    @property
    def dimensions(self) -> int: ...

    @property
    def text_format(self) -> str:
        """Names how text is written for the model, recorded with each row."""
        ...

    def embed_documents(
        self, documents: Sequence[DocumentText]
    ) -> list[list[float]]: ...

    def embed_query(self, query: str) -> list[float]: ...


def validated_vectors(
    vectors: Sequence[Sequence[float]], *, count: int, dimensions: int
) -> list[list[float]]:
    """The vectors as floats, or a specific error if any cannot be used."""
    if len(vectors) != count:
        raise EmbeddingMalformedError()
    checked: list[list[float]] = []
    for vector in vectors:
        if len(vector) != dimensions:
            raise EmbeddingDimensionError()
        values = [float(item) for item in vector]
        # Cosine distance is undefined for a vector of zeros.
        if not all(math.isfinite(item) for item in values) or not any(values):
            raise EmbeddingMalformedError()
        checked.append(values)
    return checked


class FakeEmbedder:
    """Deterministic and offline vectors made from a hash of the text.

    `failures` maps a 1-based call number to the error that call raises.
    `vectors` gives chosen vectors for exact texts, for tests about ranking.
    """

    text_format = "fake-v1"

    def __init__(
        self,
        *,
        dimensions: int = 8,
        model_name: str = "fake-embedding",
        failures: Mapping[int, ModelError] | None = None,
        vectors: Mapping[str, list[float]] | None = None,
    ) -> None:
        self._dimensions = dimensions
        self._model_name = model_name
        self._failures = dict(failures or {})
        self._vectors = dict(vectors or {})
        self._calls = 0
        self.document_calls: list[list[DocumentText]] = []
        self.query_calls: list[str] = []

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def embed_documents(self, documents: Sequence[DocumentText]) -> list[list[float]]:
        self._count_call()
        self.document_calls.append(list(documents))
        return [self._vector(document.text) for document in documents]

    def embed_query(self, query: str) -> list[float]:
        self._count_call()
        self.query_calls.append(query)
        return self._vector(query)

    def _count_call(self) -> None:
        self._calls += 1
        failure = self._failures.get(self._calls)
        if failure is not None:
            raise failure

    def _vector(self, text: str) -> list[float]:
        if text in self._vectors:
            return self._vectors[text]
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        return [(digest[i % len(digest)] + 1) / 256 for i in range(self._dimensions)]
