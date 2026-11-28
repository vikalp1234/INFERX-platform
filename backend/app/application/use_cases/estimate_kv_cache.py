from app.application.ports.outbound.model_execution import ModelExecutionPort
from app.domain.inference.kv_cache import KvCacheEstimate, estimate_kv_cache


class EstimateKvCache:
    """Derive KV-cache size for ``tokens`` from the loaded model's architecture."""

    def __init__(self, execution: ModelExecutionPort) -> None:
        self._execution = execution

    def execute(self, tokens: int) -> KvCacheEstimate:
        return estimate_kv_cache(self._execution.architecture(), tokens)
