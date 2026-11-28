from app.domain.exceptions import InferenceFailedError, ModelLoadError, ModelNotLoadedError
from app.domain.inference.generation import (
    GenerationConfig,
    GenerationResult,
    TokenizationResult,
)
from app.domain.inference.kv_cache import ModelArchitecture
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
    ) -> None:
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

    def generate(self, prompt: str, config: GenerationConfig) -> GenerationResult:
        self.calls.append("generate")
        if not self._loaded:
            raise ModelNotLoadedError("model is not loaded")
        if self.fail_generate:
            raise InferenceFailedError("generation failed")
        self.configs.append(config)
        output_tokens = min(config.max_new_tokens, 3)
        text = "fake output"
        if not config.is_greedy and config.seed is not None:
            text += f" {config.seed % 1000}"
        stamps = tuple((i + 1) * self.tick_ns for i in range(output_tokens))
        timings = GenerationTimings(0, stamps, (output_tokens + 1) * self.tick_ns)
        return GenerationResult(
            text=text,
            prompt_tokens=self.tokenize(prompt).count,
            output_tokens=output_tokens,
            timings=timings,
        )

    def architecture(self) -> ModelArchitecture:
        self.calls.append("architecture")
        if not self._loaded:
            raise ModelNotLoadedError("model is not loaded")
        return self.ARCHITECTURE
