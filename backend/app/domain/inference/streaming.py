from dataclasses import dataclass

from app.domain.inference.generation import GenerationResult


@dataclass(frozen=True)
class TokenDelta:
    """A piece of generated text. ``index`` counts deltas (0, 1, 2, ...), not tokens."""

    index: int
    text: str


@dataclass(frozen=True)
class StreamFinished:
    """Terminal item of a stream; carries the full result."""

    result: GenerationResult


StreamItem = TokenDelta | StreamFinished
