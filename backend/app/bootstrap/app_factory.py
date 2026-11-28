import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.adapters.inbound.http.body_limit import BodyLimitMiddleware
from app.adapters.inbound.http.dependencies import ApiDependencies
from app.adapters.inbound.http.errors import register_error_handlers
from app.adapters.inbound.http.generate import generate_router
from app.adapters.inbound.http.health import health_router
from app.adapters.inbound.http.model import model_router
from app.adapters.inbound.http.request_id import RequestIdMiddleware
from app.adapters.inbound.http.tokenize import tokenize_router
from app.bootstrap.container import Container, build_container
from app.domain.exceptions import InferxError
from app.infrastructure.config.settings import Settings

logger = logging.getLogger(__name__)


def create_app(container: Container | None = None) -> FastAPI:
    """Build the API. The model loads at startup only when INFERX_AUTOLOAD_MODEL is true."""
    container = container or build_container(Settings())

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        if container.settings.autoload_model:
            try:
                container.load_model.execute(container.settings.to_model_spec())
            except InferxError as exc:
                logger.error("autoload_failed", extra={"error_type": type(exc).__name__})
        yield

    app = FastAPI(title="INFERX", lifespan=lifespan)
    app.state.container = container
    app.state.api_deps = ApiDependencies(
        tokenize_prompt=container.tokenize_prompt,
        generate_text=container.generate_text,
        stream_generation=container.stream_generation,
        get_model_status=container.get_model_status,
        estimate_kv_cache=container.estimate_kv_cache,
    )
    # Added last = outermost: the request ID is set before anything else runs.
    app.add_middleware(BodyLimitMiddleware, max_bytes=container.settings.max_body_bytes)
    app.add_middleware(RequestIdMiddleware)
    register_error_handlers(app)
    app.include_router(health_router)
    app.include_router(model_router)
    app.include_router(tokenize_router)
    app.include_router(generate_router)
    return app
