"""The Gemini embedding adapter against a stubbed HTTP layer (R2; FR-RET-005). Offline."""

import json
from collections.abc import Callable
from typing import Any

import httpx
import pytest

from app.config import Settings
from app.services.embeddings import (
    DocumentText,
    Embedder,
    EmbeddingDimensionError,
    EmbeddingMalformedError,
    EmbeddingNotConfiguredError,
)
from app.services.embeddings_gemini import GeminiEmbedder
from app.services.llm import (
    ModelAuthenticationError,
    ModelError,
    ModelRateLimitError,
    ModelTimeoutError,
    ModelUnavailableError,
)
from app.services.llm_factory import build_embedder

KEY = "test-key-not-real"
BASE = "https://gemini.test"
MODEL = "gemini-embedding-2"
Handler = Callable[[httpx.Request], httpx.Response]
DOC = DocumentText(title="Ice Studies", text="Glaciers retreated.")


def embedder(handler: Handler, *, dimensions: int = 2) -> GeminiEmbedder:
    return GeminiEmbedder(
        model=MODEL,
        api_key=KEY,
        base_url=BASE,
        dimensions=dimensions,
        timeout_seconds=9.0,
        transport=httpx.MockTransport(handler),
    )


def vectors(*values: list[float]) -> httpx.Response:
    return httpx.Response(200, json={"embeddings": [{"values": v} for v in values]})


def capture(sent: list[httpx.Request], response: httpx.Response) -> Handler:
    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        return response

    return handler


def test_it_satisfies_the_interface() -> None:
    adapter: Embedder = embedder(lambda _: vectors([1.0, 0.0]))

    assert adapter.model_name == MODEL
    assert adapter.dimensions == 2
    assert adapter.text_format == "gemini-embedding-2-retrieval-v1"


def test_documents_are_sent_as_one_batch_in_the_documented_form() -> None:
    sent: list[httpx.Request] = []
    no_title = DocumentText(title=None, text="Rocks moved.")

    result = embedder(capture(sent, vectors([1.0, 0.0], [0.0, 1.0]))).embed_documents(
        [DOC, no_title]
    )

    assert result == [[1.0, 0.0], [0.0, 1.0]]
    [request] = sent
    assert request.method == "POST"
    assert str(request.url) == f"{BASE}/v1beta/models/{MODEL}:batchEmbedContents"
    assert request.headers["x-goog-api-key"] == KEY
    assert json.loads(request.content) == {
        "requests": [
            {
                "model": f"models/{MODEL}",
                "content": {
                    "parts": [
                        {"text": "title: Ice Studies | text: Glaciers retreated."}
                    ]
                },
                "output_dimensionality": 2,
            },
            {
                "model": f"models/{MODEL}",
                "content": {"parts": [{"text": "title: none | text: Rocks moved."}]},
                "output_dimensionality": 2,
            },
        ]
    }


def test_a_query_uses_the_query_form() -> None:
    sent: list[httpx.Request] = []

    result = embedder(capture(sent, vectors([1.0, 0.0]))).embed_query("Why?")

    assert result == [1.0, 0.0]
    [entry] = json.loads(sent[0].content)["requests"]
    assert entry["content"] == {
        "parts": [{"text": "task: search result | query: Why?"}]
    }


def test_the_timeout_is_applied() -> None:
    sent: list[httpx.Request] = []

    embedder(capture(sent, vectors([1.0, 0.0]))).embed_query("Why?")

    assert sent[0].extensions["timeout"]["read"] == 9.0


def test_no_documents_means_no_request() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise AssertionError("no request expected")

    assert embedder(handler).embed_documents([]) == []


@pytest.mark.parametrize(
    ("status", "error"),
    [
        (401, ModelAuthenticationError),
        (403, ModelAuthenticationError),
        (429, ModelRateLimitError),
        (500, ModelUnavailableError),
        (504, ModelTimeoutError),
    ],
)
def test_each_status_is_a_specific_error_without_provider_text(
    status: int, error: type[ModelError]
) -> None:
    secret = "provider detail with paper text"

    with pytest.raises(error) as caught:
        embedder(lambda _: httpx.Response(status, text=secret)).embed_query("Why?")

    assert secret not in str(caught.value)
    assert KEY not in str(caught.value)


@pytest.mark.parametrize(
    ("raised", "error"),
    [
        (httpx.ReadTimeout("slow"), ModelTimeoutError),
        (httpx.ConnectError("down"), ModelUnavailableError),
    ],
)
def test_transport_failures_are_specific_errors(
    raised: Exception, error: type[ModelError]
) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise raised

    with pytest.raises(error):
        embedder(handler).embed_query("Why?")


@pytest.mark.parametrize(
    "response",
    [
        pytest.param(httpx.Response(200, text="not json"), id="not json"),
        pytest.param(httpx.Response(200, json={}), id="no embeddings"),
        pytest.param(httpx.Response(200, json=[1]), id="wrong shape"),
        pytest.param(httpx.Response(200, json={"embeddings": [{}]}), id="no values"),
        pytest.param(
            httpx.Response(200, json={"embeddings": [{"values": ["a", "b"]}]}),
            id="not numbers",
        ),
        pytest.param(httpx.Response(200, json={"embeddings": []}), id="empty"),
    ],
)
def test_a_malformed_response_is_refused(response: httpx.Response) -> None:
    with pytest.raises(EmbeddingMalformedError):
        embedder(lambda _: response).embed_query("Why?")


def test_the_wrong_dimension_is_refused() -> None:
    with pytest.raises(EmbeddingDimensionError):
        embedder(lambda _: vectors([1.0, 0.0, 0.0])).embed_query("Why?")


def settings(**values: Any) -> Settings:
    fields: dict[str, Any] = {
        "postgres_password": "x",
        "llm_api_key": KEY,
        "embedding_provider": "gemini",
        "embedding_model": MODEL,
        "embedding_dimensions": 768,
        **values,
    }
    return Settings(_env_file=None, **fields)


def test_the_factory_builds_the_configured_embedder() -> None:
    built = build_embedder(settings())

    assert isinstance(built, GeminiEmbedder)
    assert (built.model_name, built.dimensions) == (MODEL, 768)


@pytest.mark.parametrize(
    "values",
    [
        pytest.param({"llm_api_key": None}, id="no key"),
        pytest.param({"embedding_provider": "other"}, id="unknown provider"),
    ],
)
def test_an_incomplete_configuration_is_explicit(values: dict[str, Any]) -> None:
    with pytest.raises(EmbeddingNotConfiguredError):
        build_embedder(settings(**values))
