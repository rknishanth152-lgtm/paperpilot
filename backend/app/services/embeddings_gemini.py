"""The Gemini implementation of `Embedder` (R2; OQ-012, FR-RET-005).

Uses Google's REST API over httpx, so it adds no dependency. `gemini-embedding-2`
takes the retrieval task as text in the input rather than a `task_type` field.
Details and what the documentation leaves unstated: docs/design/embeddings.md.

On Google's free tier, content is used to improve Google's products and human
reviewers may read it, so use it only with open-access papers (NFR-PRI-001).

Every failure becomes a specific `ModelError` with no provider text attached.
"""

from collections.abc import Sequence
from typing import Any

import httpx

from app.services.embeddings import (
    DocumentText,
    EmbeddingMalformedError,
    validated_vectors,
)
from app.services.llm import ModelTimeoutError, ModelUnavailableError
from app.services.llm_gemini import STATUS_ERRORS

TEXT_FORMAT = "gemini-embedding-2-retrieval-v1"


def _document_text(document: DocumentText) -> str:
    return f"title: {document.title or 'none'} | text: {document.text}"


def _query_text(query: str) -> str:
    return f"task: search result | query: {query}"


class GeminiEmbedder:
    text_format = TEXT_FORMAT

    def __init__(
        self,
        *,
        model: str,
        api_key: str,
        base_url: str,
        dimensions: int,
        timeout_seconds: float,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._model = model
        self._api_key = api_key
        self._url = f"{base_url.rstrip('/')}/v1beta/models/{model}:batchEmbedContents"
        self._dimensions = dimensions
        self._timeout = timeout_seconds
        self._transport = transport

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def embed_documents(self, documents: Sequence[DocumentText]) -> list[list[float]]:
        if not documents:
            return []
        return self._embed([_document_text(document) for document in documents])

    def embed_query(self, query: str) -> list[float]:
        return self._embed([_query_text(query)])[0]

    def _embed(self, texts: list[str]) -> list[list[float]]:
        body = {
            "requests": [
                {
                    "model": f"models/{self._model}",
                    "content": {"parts": [{"text": text}]},
                    "output_dimensionality": self._dimensions,
                }
                for text in texts
            ]
        }
        try:
            with httpx.Client(
                transport=self._transport, timeout=self._timeout
            ) as client:
                response = client.post(
                    self._url, json=body, headers={"x-goog-api-key": self._api_key}
                )
        except httpx.TimeoutException:
            raise ModelTimeoutError() from None
        except httpx.TransportError:
            raise ModelUnavailableError() from None

        if response.status_code != 200:
            raise STATUS_ERRORS.get(response.status_code, ModelUnavailableError)()
        return validated_vectors(
            self._read(response), count=len(texts), dimensions=self._dimensions
        )

    @staticmethod
    def _read(response: httpx.Response) -> list[list[float]]:
        try:
            data: Any = response.json()
            return [
                [float(value) for value in entry["values"]]
                for entry in data["embeddings"]
            ]
        except ValueError, KeyError, TypeError, AttributeError:
            raise EmbeddingMalformedError() from None
