import logging

from app.application.dto.limits import InputLimits
from app.application.ports.outbound.model_execution import ModelExecutionPort
from app.application.services.request_gate import RequestGate
from app.application.use_cases.validation import validate_prompt
from app.domain.exceptions import InvalidGenerationConfigError
from app.domain.inference.generation import GenerationConfig, GenerationResult

logger = logging.getLogger(__name__)


class GenerateText:
    def __init__(
        self,
        execution: ModelExecutionPort,
        limits: InputLimits,
        gate: RequestGate | None = None,
    ) -> None:
        self._execution = execution
        self._limits = limits
        self._gate = gate

    def execute(self, prompt: str, config: GenerationConfig) -> GenerationResult:
        validate_prompt(prompt, self._limits)
        if config.max_new_tokens > self._limits.max_new_tokens:
            raise InvalidGenerationConfigError(
                f"max_new_tokens exceeds limit of {self._limits.max_new_tokens}"
            )
        slot = self._gate.acquire() if self._gate is not None else None
        try:
            result = self._execution.generate(prompt, config)
        except Exception as exc:
            logger.error("generation_failed", extra={"error_type": type(exc).__name__})
            raise
        finally:
            if slot is not None:
                slot.release()
        extra: dict[str, object] = {
            "prompt_tokens": result.prompt_tokens,
            "output_tokens": result.output_tokens,
        }
        if result.timings is not None:
            extra.update(
                ttft_ms=result.timings.ttft_ms,
                tpot_ms=result.timings.tpot_ms,
                decode_tps=result.timings.decode_tps,
                total_ms=result.timings.total_ms,
            )
        logger.info("generation_completed", extra=extra)
        return result
