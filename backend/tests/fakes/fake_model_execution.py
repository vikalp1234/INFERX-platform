import threading
import time
from collections.abc import Iterator

from app.domain.exceptions import InferenceFailedError, ModelLoadError, ModelNotLoadedError
from app.domain.inference.generation import (
    FinishReason,
    GenerationConfig,
    GenerationResult,
    TokenizationResult,
)
from app.domain.inference.kv_cache import ModelArchitecture
from app.domain.inference.streaming import StreamFinished, StreamItem, TokenDelta
from app.domain.inference.timings import GenerationTimings
from app.domain.models.model_spec import ModelSpec

MISSING_MODEL_ID = "invalid/does-not-exist"


class FakeModelExecution:
    """In-memory ModelExecutionPort for tests. Whitespace tokenizer.

    Timings come from a synthetic clock (``tick_ns`` per step) and are test fixtures,
    not measurements.
    """

    ARCHITECTURE = ModelArchitecture(num_layers=2, num_kv_heads=2, head_dim=4, dtype_bytes=2)

    def __init__(
        self,
        fail_load: bool = False,
        fail_generate: bool = False,
        tick_ns: int = 1_000_000,
        delay_s: float = 0.0,
        fail_after: int | None = None,
        n_pieces: int = 3,
    ) -> None:
        self.n_pieces = n_pieces  # how many tokens a full generation produces
        self.delay_s = delay_s  # sleep before each streamed delta
        self.fail_after = fail_after  # raise after this many streamed deltas
        self.cancel_observed = False
        self.deltas_sent = 0
        self.streams_closed = 0
        self.tick_ns = tick_ns
        self.configs: list[GenerationConfig] = []
        self.fail_load = fail_load
        self.fail_generate = fail_generate
        self.calls: list[str] = []
        self._loaded = False

    def load(self, spec: ModelSpec) -> None:
        self.calls.append("load")
        if self.fail_load or spec.model_id == MISSING_MODEL_ID:
            self._loaded = False
            raise ModelLoadError("model could not be loaded")
        self._loaded = True

    def unload(self) -> None:
        self.calls.append("unload")
        self._loaded = False

    def is_loaded(self) -> bool:
        return self._loaded

    def tokenize(self, text: str) -> TokenizationResult:
        self.calls.append("tokenize")
        if not self._loaded:
            raise ModelNotLoadedError("model is not loaded")
        return TokenizationResult(tuple(range(len(text.split()))) or (0,))

    def _pieces(self, config: GenerationConfig) -> list[str]:
        base = ["fake", " output", " text"] + [f" w{i}" for i in range(3, self.n_pieces)]
        pieces = base[: min(self.n_pieces, config.max_new_tokens)]
        if not config.is_greedy and config.seed is not None:
            pieces[0] = f"fake{config.seed % 1000}"
        return pieces

    def _finish_reason(self, config: GenerationConfig, n: int) -> FinishReason:
        return FinishReason.LENGTH if n == config.max_new_tokens else FinishReason.STOP

    def _result(self, prompt: str, config: GenerationConfig, pieces: list[str], reason):
        n = len(pieces)
        stamps = tuple((i + 1) * self.tick_ns for i in range(n))
        return GenerationResult(
            text="".join(pieces),
            prompt_tokens=self.tokenize(prompt).count,
            output_tokens=n,
            timings=GenerationTimings(0, stamps, (n + 1) * self.tick_ns),
            finish_reason=reason,
        )

    def generate(self, prompt: str, config: GenerationConfig) -> GenerationResult:
        self.calls.append("generate")
        if not self._loaded:
            raise ModelNotLoadedError("model is not loaded")
        if self.fail_generate:
            raise InferenceFailedError("generation failed")
        self.configs.append(config)
        pieces = self._pieces(config)
        return self._result(prompt, config, pieces, self._finish_reason(config, len(pieces)))

    def stream_generate(
        self, prompt: str, config: GenerationConfig, cancel: threading.Event | None = None
    ) -> Iterator[StreamItem]:
        self.calls.append("stream_generate")
        if not self._loaded:
            raise ModelNotLoadedError("model is not loaded")
        self.configs.append(config)
        sent: list[str] = []
        try:
            for index, piece in enumerate(self._pieces(config)):
                if cancel is not None and cancel.is_set():
                    self.cancel_observed = True
                    yield StreamFinished(self._result(prompt, config, sent, FinishReason.CANCELLED))
                    return
                if self.delay_s:
                    time.sleep(self.delay_s)
                if self.fail_after is not None and index >= self.fail_after:
                    raise InferenceFailedError("generation failed")
                sent.append(piece)
                self.deltas_sent += 1
                yield TokenDelta(index, piece)
            reason = self._finish_reason(config, len(sent))
            if cancel is not None and cancel.is_set():
                self.cancel_observed = True
                reason = FinishReason.CANCELLED
            yield StreamFinished(self._result(prompt, config, sent, reason))
        finally:
            self.streams_closed += 1

    def architecture(self) -> ModelArchitecture:
        self.calls.append("architecture")
        if not self._loaded:
            raise ModelNotLoadedError("model is not loaded")
        return self.ARCHITECTURE
