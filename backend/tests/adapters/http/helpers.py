import logging

from fastapi import FastAPI

from app.adapters.inbound.http.body_limit import BodyLimitMiddleware
from app.adapters.inbound.http.errors import register_error_handlers
from app.adapters.inbound.http.request_id import RequestIdMiddleware
from app.adapters.inbound.http.schemas import GenerateRequest
from app.application.request_context import request_id_var
from app.domain.exceptions import (
    InferenceFailedError,
    InvalidGenerationConfigError,
    InvalidPromptError,
    ModelLoadError,
    ModelNotLoadedError,
    OverloadedError,
)

RAISERS = {
    "invalid_prompt": InvalidPromptError("prompt must not be empty"),
    "invalid_config": InvalidGenerationConfigError("top_p must be in (0, 1]"),
    "not_loaded": ModelNotLoadedError("model is not loaded"),
    "overloaded": OverloadedError("server is at capacity"),
    "inference": InferenceFailedError("generation failed (RuntimeError)"),
    "load": ModelLoadError("model could not be loaded"),
}


def make_test_app(max_body_bytes: int = 2048) -> FastAPI:
    app = FastAPI()
    app.add_middleware(BodyLimitMiddleware, max_bytes=max_body_bytes)
    app.add_middleware(RequestIdMiddleware)
    register_error_handlers(app)

    @app.post("/echo")
    def echo(body: GenerateRequest) -> dict:
        body.to_config()
        return {"ok": True}

    @app.get("/raise/{kind}")
    def raise_kind(kind: str) -> dict:
        raise RAISERS[kind]

    @app.get("/boom")
    def boom() -> dict:
        raise RuntimeError("boom SECRET-MARKER")

    @app.get("/rid")
    def rid() -> dict:
        logging.getLogger("test").info("inside_request")
        return {"request_id": request_id_var.get()}

    return app
