"""Stable error envelope: {"error": {"code", "message", "request_id"}}.

Messages are fixed strings or domain messages; they never echo user input.
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.adapters.inbound.http.request_id import new_request_id
from app.domain.exceptions import (
    InferenceFailedError,
    InferxError,
    InvalidGenerationConfigError,
    InvalidPromptError,
    ModelNotLoadedError,
    OverloadedError,
)


def envelope_body(code: str, message: str, request_id: str) -> dict:
    return {"error": {"code": code, "message": message, "request_id": request_id}}


def request_id_of(request: Request) -> str:
    return getattr(request.state, "request_id", None) or new_request_id()


def error_response(
    status: int,
    code: str,
    message: str,
    request_id: str,
    extra_headers: dict[str, str] | None = None,
) -> JSONResponse:
    headers = {"X-Request-ID": request_id, **(extra_headers or {})}
    return JSONResponse(envelope_body(code, message, request_id), status, headers)


def describe_error(exc: Exception) -> tuple[int, str, str]:
    """Map an exception to (status, code, message). Never includes user input."""
    if isinstance(exc, InvalidPromptError | InvalidGenerationConfigError):
        return 422, "invalid_request", str(exc)
    if isinstance(exc, ModelNotLoadedError):
        return 409, "model_not_loaded", "model is not loaded"
    if isinstance(exc, OverloadedError):
        return 429, "overloaded", "server is at capacity"
    if isinstance(exc, InferenceFailedError):
        return 500, "inference_failed", "inference failed"
    return 500, "internal_error", "internal error"


def _domain_response(exc: InferxError, request_id: str) -> JSONResponse:
    status, code, message = describe_error(exc)
    headers = {"Retry-After": "1"} if status == 429 else None
    return error_response(status, code, message, request_id, headers)


_HTTP_CODES = {404: "not_found", 405: "method_not_allowed", 413: "payload_too_large"}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        fields = sorted(
            {str(part) for e in exc.errors() for part in e["loc"][-1:] if isinstance(part, str)}
        )
        detail = f" (fields: {', '.join(fields)})" if fields else ""
        return error_response(
            422, "invalid_request", f"request validation failed{detail}", request_id_of(request)
        )

    @app.exception_handler(InferxError)
    async def _domain(request: Request, exc: InferxError) -> JSONResponse:
        return _domain_response(exc, request_id_of(request))

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = _HTTP_CODES.get(exc.status_code, "http_error")
        message = "payload too large" if exc.status_code == 413 else code.replace("_", " ")
        return error_response(exc.status_code, code, message, request_id_of(request))

    @app.exception_handler(Exception)
    async def _unexpected(request: Request, exc: Exception) -> JSONResponse:
        return error_response(500, "internal_error", "internal error", request_id_of(request))
