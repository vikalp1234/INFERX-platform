from typing import Protocol

from app.domain.inference.generation import (
    GenerationConfig,
    GenerationResult,
    TokenizationResult,
)
from app.domain.inference.kv_cache import ModelArchitecture
from app.domain.models.model_spec import ModelSpec


class ModelExecutionPort(Protocol):
    """What use cases need from a model runtime.

    Contract:
    - ``load`` failure raises ``ModelLoadError`` and leaves the port unloaded.
    - ``tokenize``/``generate`` before a successful load raise ``ModelNotLoadedError``.
    - Runtime failures raise ``InferenceFailedError``.
    - ``unload`` is idempotent.
    - ``generate`` returns timings with one stamp per output token; ``architecture``
      requires a loaded model.
    """

    def load(self, spec: ModelSpec) -> None: ...

    def unload(self) -> None: ...

    def is_loaded(self) -> bool: ...

    def tokenize(self, text: str) -> TokenizationResult: ...

    def generate(self, prompt: str, config: GenerationConfig) -> GenerationResult: ...

    def architecture(self) -> ModelArchitecture: ...
