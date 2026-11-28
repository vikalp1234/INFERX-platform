from fastapi import APIRouter

from app.adapters.inbound.http.dependencies import Deps
from app.adapters.inbound.http.schemas import ModelStatusResponse

model_router = APIRouter(prefix="/v1")


@model_router.get("/model", response_model=ModelStatusResponse)
def model_status(deps: Deps) -> ModelStatusResponse:
    status = deps.get_model_status.execute()
    return ModelStatusResponse(
        loaded=status.loaded, model_id=status.model_id, revision=status.revision
    )
