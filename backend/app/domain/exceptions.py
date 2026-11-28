"""Domain errors. Messages must never contain prompts or generated text."""


class InferxError(Exception):
    """Base class for all expected INFERX errors."""


class InvalidModelSpecError(InferxError):
    """The model specification is not acceptable."""


class InvalidPromptError(InferxError):
    """The prompt is empty or exceeds the configured limit."""


class InvalidGenerationConfigError(InferxError):
    """The generation configuration is outside allowed bounds."""


class ModelLoadError(InferxError):
    """The model could not be loaded."""


class ModelNotLoadedError(InferxError):
    """An operation needs a loaded model."""


class InferenceFailedError(InferxError):
    """Inference failed at runtime."""


class InvalidTimingError(InferxError):
    """Raised when raw timing stamps are inconsistent (non-monotonic)."""


class InvalidArchitectureError(InferxError):
    """Raised for an invalid model architecture description or KV-cache input."""


class OverloadedError(InferxError):
    """The service is at capacity; the request was not (or could not be) admitted."""
