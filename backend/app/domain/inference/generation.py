from dataclasses import dataclass

from app.domain.exceptions import InvalidGenerationConfigError


@dataclass(frozen=True)
class GenerationConfig:
    """Greedy generation settings (sampling controls arrive in v0.2.0)."""

    max_new_tokens: int = 64

    def __post_init__(self) -> None:
        if self.max_new_tokens < 1:
            raise InvalidGenerationConfigError("max_new_tokens must be >= 1")


@dataclass(frozen=True)
class GenerationResult:
    text: str
    prompt_tokens: int
    output_tokens: int


@dataclass(frozen=True)
class TokenizationResult:
    token_ids: tuple[int, ...]

    @property
    def count(self) -> int:
        return len(self.token_ids)
