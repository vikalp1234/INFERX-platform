from fastapi import APIRouter, Request

from app.adapters.inbound.http.dependencies import Deps
from app.adapters.inbound.http.errors import request_id_of
from app.adapters.inbound.http.schemas import TokenizeRequest, TokenizeResponse

tokenize_router = APIRouter(prefix="/v1")


@tokenize_router.post("/tokenize", response_model=TokenizeResponse)
def tokenize(
    body: TokenizeRequest,
    request: Request,
    deps: Deps,
) -> TokenizeResponse:
    result = deps.tokenize_prompt.execute(body.prompt)
    return TokenizeResponse(
        request_id=request_id_of(request),
        token_count=result.count,
        token_ids=list(result.token_ids),
    )
