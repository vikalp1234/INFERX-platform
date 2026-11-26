from fastapi import APIRouter

health_router = APIRouter()


@health_router.get("/health")
def health() -> dict[str, str]:
    """Process liveness only; does not check the model or any dependency."""
    return {"status": "ok"}
