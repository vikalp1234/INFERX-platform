"""Typed request/response schemas (pydantic lives only in the adapter layer)."""

from typing import Any

from pydantic import BaseModel, ConfigDict

from app.domain.inference.generation import GenerationConfig


class _Request(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class TokenizeRequest(_Request):
    prompt: str


class TokenizeResponse(BaseModel):
    request_id: str
    token_count: int
    token_ids: list[int]


class GenerateRequest(_Request):
    prompt: str
    max_new_tokens: int = 64
    temperature: float = 0.0
    top_k: int | None = None
    top_p: float | None = None
    repetition_penalty: float = 1.0
    seed: int | None = None

    def to_config(self) -> GenerationConfig:
        return GenerationConfig(
            max_new_tokens=self.max_new_tokens,
            temperature=self.temperature,
            top_k=self.top_k,
            top_p=self.top_p,
            repetition_penalty=self.repetition_penalty,
            seed=self.seed,
        )


class GenerateResponse(BaseModel):
    request_id: str
    text: str
    finish_reason: str | None
    prompt_tokens: int
    output_tokens: int
    metrics: dict[str, Any]


class ModelStatusResponse(BaseModel):
    loaded: bool
    model_id: str
    revision: str


class ErrorBody(BaseModel):
    code: str
    message: str
    request_id: str


class ErrorEnvelope(BaseModel):
    error: ErrorBody
