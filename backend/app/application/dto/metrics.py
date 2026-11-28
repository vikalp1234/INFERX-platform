"""Run metrics with an explicit provenance label on every value."""

from dataclasses import dataclass
from typing import Any

from app.domain.inference.generation import GenerationResult
from app.domain.inference.kv_cache import KvCacheEstimate

MEASURED = "measured"


@dataclass(frozen=True)
class RunMetrics:
    result: GenerationResult
    kv_cache: KvCacheEstimate | None = None

    @classmethod
    def from_result(
        cls, result: GenerationResult, kv_cache: KvCacheEstimate | None = None
    ) -> "RunMetrics":
        return cls(result, kv_cache)

    def to_dict(self) -> dict[str, Any]:
        timings = self.result.timings
        data: dict[str, Any] = {
            "prompt_tokens": _labelled(self.result.prompt_tokens),
            "output_tokens": _labelled(self.result.output_tokens),
            "ttft_ms": _labelled(timings.ttft_ms if timings else None),
            "tpot_ms": _labelled(timings.tpot_ms if timings else None),
            "decode_tps": _labelled(timings.decode_tps if timings else None),
            "total_ms": _labelled(timings.total_ms if timings else None),
        }
        if self.kv_cache is not None:
            data["kv_cache_bytes_estimate"] = _labelled(
                self.kv_cache.bytes, self.kv_cache.provenance
            )
        return data


def _labelled(value: Any, provenance: str = MEASURED) -> dict[str, Any]:
    return {"value": value, "provenance": provenance}
