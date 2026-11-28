from fastapi import FastAPI

from app.adapters.inbound.http.health import health_router
from app.bootstrap.container import Container, build_container
from app.infrastructure.config.settings import Settings


def create_app(container: Container | None = None) -> FastAPI:
    """Build the API. The model is not loaded at startup."""
    container = container or build_container(Settings())
    app = FastAPI(title="INFERX")
    app.state.container = container
    app.include_router(health_router)
    return app
