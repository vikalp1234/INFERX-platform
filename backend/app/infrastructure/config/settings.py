from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.application.dto.limits import InputLimits
from app.application.services.request_gate import GateConfig
from app.domain.models.model_spec import ModelSpec


class Settings(BaseSettings):
    """Environment-driven configuration. Secrets are never defaulted here."""

    model_config = SettingsConfigDict(env_prefix="INFERX_", env_file=".env", extra="ignore")

    env: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"
    model_id: str = "HuggingFaceTB/SmolLM2-360M-Instruct"
    model_revision: str = "a10cc1512eabd3dde888204e902eca88bddb4951"
    max_prompt_chars: int = Field(default=4000, ge=1)
    max_new_tokens: int = Field(default=256, ge=1)
    autoload_model: bool = False
    max_concurrent_requests: int = Field(default=1, ge=1)
    max_waiting_requests: int = Field(default=4, ge=0)
    queue_wait_timeout_s: float = Field(default=30.0, gt=0)
    max_body_bytes: int = Field(default=65536, ge=1024)

    def to_model_spec(self) -> ModelSpec:
        return ModelSpec(model_id=self.model_id, revision=self.model_revision)

    def to_input_limits(self) -> InputLimits:
        return InputLimits(
            max_prompt_chars=self.max_prompt_chars, max_new_tokens=self.max_new_tokens
        )

    def to_gate_config(self) -> GateConfig:
        return GateConfig(
            max_concurrent=self.max_concurrent_requests,
            max_waiting=self.max_waiting_requests,
            wait_timeout_s=self.queue_wait_timeout_s,
        )
