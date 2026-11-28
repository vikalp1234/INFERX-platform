"""What the HTTP routes need. Populated by the composition root (bootstrap)."""

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request

from app.application.use_cases.estimate_kv_cache import EstimateKvCache
from app.application.use_cases.generate_text import GenerateText
from app.application.use_cases.get_model_status import GetModelStatus
from app.application.use_cases.stream_generation import StreamGeneration
from app.application.use_cases.tokenize_prompt import TokenizePrompt


@dataclass
class ApiDependencies:
    tokenize_prompt: TokenizePrompt
    generate_text: GenerateText
    stream_generation: StreamGeneration
    get_model_status: GetModelStatus
    estimate_kv_cache: EstimateKvCache


def get_api_dependencies(request: Request) -> ApiDependencies:
    return request.app.state.api_deps


Deps = Annotated[ApiDependencies, Depends(get_api_dependencies)]
