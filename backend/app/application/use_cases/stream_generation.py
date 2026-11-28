import logging
import threading
from collections.abc import Iterator

from app.application.dto.limits import InputLimits
from app.application.ports.outbound.model_execution import ModelExecutionPort
from app.application.services.request_gate import RequestGate
from app.application.use_cases.validation import validate_prompt
from app.domain.exceptions import InvalidGenerationConfigError, ModelNotLoadedError
from app.domain.inference.generation import GenerationConfig
from app.domain.inference.streaming import StreamFinished, StreamItem

logger = logging.getLogger(__name__)


class StreamGeneration:
    def __init__(
        self, execution: ModelExecutionPort, limits: InputLimits, gate: RequestGate
    ) -> None:
        self._execution = execution
        self._limits = limits
        self._gate = gate

    def execute(
        self, prompt: str, config: GenerationConfig, cancel: threading.Event | None = None
    ) -> Iterator[StreamItem]:
        """Validate and pre-check eagerly (so callers can fail before streaming starts)."""
        validate_prompt(prompt, self._limits)
        if config.max_new_tokens > self._limits.max_new_tokens:
            raise InvalidGenerationConfigError(
                f"max_new_tokens exceeds limit of {self._limits.max_new_tokens}"
            )
        if not self._execution.is_loaded():
            raise ModelNotLoadedError("model is not loaded")
        self._gate.check_capacity()
        return self._run(prompt, config, cancel)

    def _run(
        self, prompt: str, config: GenerationConfig, cancel: threading.Event | None
    ) -> Iterator[StreamItem]:
        slot = self._gate.acquire()
        inner = None
        try:
            inner = self._execution.stream_generate(prompt, config, cancel)
            for item in inner:
                yield item
                if isinstance(item, StreamFinished):
                    self._log_finished(item)
        except GeneratorExit:
            raise
        except Exception as exc:
            logger.error("stream_failed", extra={"error_type": type(exc).__name__})
            raise
        finally:
            if inner is not None:
                inner.close()
            slot.release()

    @staticmethod
    def _log_finished(item: StreamFinished) -> None:
        result = item.result
        extra: dict[str, object] = {
            "prompt_tokens": result.prompt_tokens,
            "output_tokens": result.output_tokens,
            "finish_reason": str(result.finish_reason) if result.finish_reason else None,
        }
        if result.timings is not None:
            extra.update(ttft_ms=result.timings.ttft_ms, total_ms=result.timings.total_ms)
        logger.info("stream_completed", extra=extra)
