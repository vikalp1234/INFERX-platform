import threading
from collections.abc import Iterator
from typing import Protocol

from app.domain.inference.generation import (
    GenerationConfig,
    GenerationResult,
    TokenizationResult,
)
from app.domain.inference.kv_cache import ModelArchitecture
from app.domain.inference.streaming import StreamItem
from app.domain.models.model_spec import ModelSpec


class ModelExecutionPort(Protocol):
    """What use cases need from a model runtime.

    Contract:
    - ``load`` failure raises ``ModelLoadError`` and leaves the port unloaded.
    - ``tokenize``/``generate`` before a successful load raise ``ModelNotLoadedError``.
    - Runtime failures raise ``InferenceFailedError``.
    - ``unload`` is idempotent.
    - ``stream_generate`` yields zero or more ``TokenDelta`` (indices 0, 1, 2, ...) then
      exactly one ``StreamFinished``; setting ``cancel`` ends it early with
      ``finish_reason=CANCELLED``; it raises ``ModelNotLoadedError`` on the first step when
      unloaded; closing the iterator early stops the work and frees the port.
    - ``generate`` returns timings with one stamp per output token; ``architecture``
      requires a loaded model.
    """

    def load(self, spec: ModelSpec) -> None: ...

    def unload(self) -> None: ...

    def is_loaded(self) -> bool: ...

    def tokenize(self, text: str) -> TokenizationResult: ...

    def generate(self, prompt: str, config: GenerationConfig) -> GenerationResult: ...

    def architecture(self) -> ModelArchitecture: ...

    def stream_generate(
        self, prompt: str, config: GenerationConfig, cancel: threading.Event | None = None
    ) -> Iterator[StreamItem]: ...
