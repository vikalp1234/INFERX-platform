from app.domain.exceptions import InferenceFailedError, ModelLoadError, ModelNotLoadedError
from app.domain.inference.generation import (
    GenerationConfig,
    GenerationResult,
    TokenizationResult,
)
from app.domain.models.model_spec import ModelSpec

MISSING_MODEL_ID = "invalid/does-not-exist"


class FakeModelExecution:
    """In-memory ModelExecutionPort for tests. Whitespace tokenizer."""

    def __init__(self, fail_load: bool = False, fail_generate: bool = False) -> None:
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
        return GenerationResult(
            text="fake output",
            prompt_tokens=self.tokenize(prompt).count,
            output_tokens=min(config.max_new_tokens, 3),
        )
