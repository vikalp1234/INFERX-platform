from dataclasses import dataclass
from enum import StrEnum

from app.domain.exceptions import InvalidGenerationConfigError
from app.domain.inference.timings import GenerationTimings


class FinishReason(StrEnum):
    STOP = "stop"  # end-of-sequence token produced
    LENGTH = "length"  # max_new_tokens reached
    CANCELLED = "cancelled"  # stopped by the caller


@dataclass(frozen=True)
class GenerationConfig:
    """Generation settings.

    ``temperature == 0`` means greedy decoding; ``top_k``/``top_p`` only apply when
    sampling, so combining them with greedy is rejected rather than silently ignored.
    ``seed`` makes sampled output reproducible on the same runtime and hardware.
    """

    max_new_tokens: int = 64
    temperature: float = 0.0
    top_k: int | None = None
    top_p: float | None = None
    repetition_penalty: float = 1.0
    seed: int | None = None

    def __post_init__(self) -> None:
        if self.max_new_tokens < 1:
            raise InvalidGenerationConfigError("max_new_tokens must be >= 1")
        if self.temperature < 0:
            raise InvalidGenerationConfigError("temperature must be >= 0")
        if self.top_k is not None and (isinstance(self.top_k, bool) or self.top_k < 1):
            raise InvalidGenerationConfigError("top_k must be an integer >= 1")
        if self.top_p is not None and not 0 < self.top_p <= 1:
            raise InvalidGenerationConfigError("top_p must be in (0, 1]")
        if self.repetition_penalty <= 0:
            raise InvalidGenerationConfigError("repetition_penalty must be > 0")
        if self.seed is not None and (isinstance(self.seed, bool) or self.seed < 0):
            raise InvalidGenerationConfigError("seed must be an integer >= 0")
        if self.is_greedy and (self.top_k is not None or self.top_p is not None):
            raise InvalidGenerationConfigError(
                "top_k/top_p require temperature > 0 (temperature 0 is greedy)"
            )

    @property
    def is_greedy(self) -> bool:
        return self.temperature == 0.0


@dataclass(frozen=True)
class GenerationResult:
    text: str
    prompt_tokens: int
    output_tokens: int
    timings: GenerationTimings | None = None
    finish_reason: FinishReason | None = None


@dataclass(frozen=True)
class TokenizationResult:
    token_ids: tuple[int, ...]

    @property
    def count(self) -> int:
        return len(self.token_ids)
