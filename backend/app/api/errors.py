"""Structured API errors (NFR-SEC-005).

Every error response is `{"error": {"code", "message", "details"?}}`. Codes
are stable lowercase snake_case; messages are plain language. No stack traces,
file paths, exception text, request input or configuration reach a client.
Unexpected exceptions become `internal_error`; the server log keeps the
traceback (Starlette re-raises after this handler responds).
"""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.schemas.answer import MalformedAnswerError
from app.schemas.documents import ErrorBody, ErrorResponse
from app.services.ingestion.documents import (
    DocumentNotFoundError,
    DocumentNotParsedError,
    DocumentNotRetryableError,
)
from app.services.ingestion.validation import UploadRejectedError
from app.services.llm import ModelError
from app.services.retrieval.keyword import QueryTooLongError
from app.storage import StorageError

UPLOAD_REJECTION_STATUS = {"empty_file": 400, "file_too_large": 413, "not_pdf": 415}
MODEL_ERROR_STATUS = {
    "model_timeout": 504,
    "model_rate_limited": 429,
    "model_not_configured": 503,
}


def error_response(
    status: int, code: str, message: str, details: dict[str, Any] | None = None
) -> JSONResponse:
    body = ErrorResponse(error=ErrorBody(code=code, message=message, details=details))
    return JSONResponse(status_code=status, content=body.model_dump(exclude_none=True))


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(UploadRejectedError)
    async def upload_rejected(
        request: Request, exc: UploadRejectedError
    ) -> JSONResponse:
        return error_response(UPLOAD_REJECTION_STATUS[exc.code], exc.code, exc.message)

    @app.exception_handler(ModelError)
    async def model_failed(request: Request, exc: ModelError) -> JSONResponse:
        return error_response(
            MODEL_ERROR_STATUS.get(exc.code, 502), exc.code, exc.message
        )

    @app.exception_handler(MalformedAnswerError)
    async def malformed_answer(
        request: Request, exc: MalformedAnswerError
    ) -> JSONResponse:
        return error_response(502, exc.code, exc.message)

    @app.exception_handler(QueryTooLongError)
    async def query_too_long(request: Request, exc: QueryTooLongError) -> JSONResponse:
        return error_response(422, exc.code, exc.message)

    @app.exception_handler(StorageError)
    async def storage_failed(request: Request, exc: StorageError) -> JSONResponse:
        return error_response(
            500, "storage_error", "The file could not be stored on the server."
        )

    @app.exception_handler(DocumentNotFoundError)
    async def not_found(request: Request, exc: DocumentNotFoundError) -> JSONResponse:
        return error_response(404, "document_not_found", "No document has this id.")

    @app.exception_handler(DocumentNotParsedError)
    async def not_parsed(request: Request, exc: DocumentNotParsedError) -> JSONResponse:
        return error_response(
            409,
            "document_not_parsed",
            "The document has no structure because it is not parsed.",
            {"status": exc.status, "failure_reason": exc.failure_reason},
        )

    @app.exception_handler(DocumentNotRetryableError)
    async def not_retryable(
        request: Request, exc: DocumentNotRetryableError
    ) -> JSONResponse:
        return error_response(
            409,
            "document_not_retryable",
            "Only a failed or pending document can be retried.",
            {"status": exc.status},
        )

    @app.exception_handler(RequestValidationError)
    async def invalid_request(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # Field names only: pydantic's errors echo the submitted input.
        fields = sorted(
            {str(error["loc"][-1]) for error in exc.errors() if error["loc"]}
        )
        message = "The request is not valid."
        if fields:
            message += f" Check: {', '.join(fields)}."
        return error_response(422, "invalid_request", message)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        if exc.status_code == 404:
            return error_response(404, "not_found", "There is nothing at this address.")
        if exc.status_code == 405:
            return error_response(
                405, "method_not_allowed", "This address does not accept that method."
            )
        return error_response(exc.status_code, "http_error", "The request failed.")

    @app.exception_handler(Exception)
    async def unexpected(request: Request, exc: Exception) -> JSONResponse:
        return error_response(
            500, "internal_error", "Something went wrong on the server."
        )
