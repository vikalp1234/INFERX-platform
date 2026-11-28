"""Derived KV-cache size estimate.

The numbers here are computed from model configuration, NOT measured from the
runtime allocator. Actual memory use depends on the engine (padding, block
allocation, overhead), so treat the result as a lower-bound estimate.
"""

from dataclasses import dataclass

from app.domain.exceptions import InvalidArchitectureError


@dataclass(frozen=True)
class ModelArchitecture:
    num_layers: int
    num_kv_heads: int
    head_dim: int
    dtype_bytes: int

    def __post_init__(self) -> None:
        for name in ("num_layers", "num_kv_heads", "head_dim", "dtype_bytes"):
            if getattr(self, name) < 1:
                raise InvalidArchitectureError(f"{name} must be >= 1")


@dataclass(frozen=True)
class KvCacheEstimate:
    bytes: int
    tokens: int
    provenance: str = "derived_from_model_config"


def estimate_kv_cache(arch: ModelArchitecture, tokens: int) -> KvCacheEstimate:
    """2 (keys and values) * layers * kv_heads * head_dim * dtype_bytes * tokens."""
    if tokens < 0:
        raise InvalidArchitectureError("tokens must be >= 0")
    size = 2 * arch.num_layers * arch.num_kv_heads * arch.head_dim * arch.dtype_bytes * tokens
    return KvCacheEstimate(bytes=size, tokens=tokens)
