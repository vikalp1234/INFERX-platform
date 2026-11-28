from fastapi import APIRouter, Request

from app.adapters.inbound.http.dependencies import Deps
from app.adapters.inbound.http.errors import request_id_of
from app.adapters.inbound.http.schemas import GenerateRequest, GenerateResponse
from app.application.dto.metrics import RunMetrics

generate_router = APIRouter(prefix="/v1")


@generate_router.post("/generate", response_model=GenerateResponse)
def generate(
    body: GenerateRequest,
    request: Request,
    deps: Deps,
) -> GenerateResponse:
    result = deps.generate_text.execute(body.prompt, body.to_config())
    kv = deps.estimate_kv_cache.execute(result.prompt_tokens + result.output_tokens)
    return GenerateResponse(
        request_id=request_id_of(request),
        text=result.text,
        finish_reason=str(result.finish_reason) if result.finish_reason else None,
        prompt_tokens=result.prompt_tokens,
        output_tokens=result.output_tokens,
        metrics=RunMetrics.from_result(result, kv).to_dict(),
    )
