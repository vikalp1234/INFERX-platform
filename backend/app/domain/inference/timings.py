"""Per-request timing value object and metric definitions (CLAUDE.md section 12).

Measurement boundary (v0.2.0, Transformers adapter): ``request_start_ns`` is taken
once ``generate()`` holds the adapter lock, so it INCLUDES prompt tokenization and
host-to-device transfer and EXCLUDES any wait for the lock (queue wait). Stamps come
from ``time.perf_counter_ns()``. ``end_ns`` is when generation finished. These are
adapter-observed values, not client-observed latency.
"""

from dataclasses import dataclass

from app.domain.exceptions import InvalidTimingError

_NS_PER_MS = 1_000_000
_NS_PER_S = 1_000_000_000


@dataclass(frozen=True)
class GenerationTimings:
    request_start_ns: int
    token_timestamps_ns: tuple[int, ...]
    end_ns: int

    def __post_init__(self) -> None:
        previous = self.request_start_ns
        for stamp in self.token_timestamps_ns:
            if stamp < previous:
                raise InvalidTimingError("timing stamps must be non-decreasing")
            previous = stamp
        if self.end_ns < previous:
            raise InvalidTimingError("end time precedes last token time")

    @property
    def ttft_ms(self) -> float | None:
        if not self.token_timestamps_ns:
            return None
        return (self.token_timestamps_ns[0] - self.request_start_ns) / _NS_PER_MS

    @property
    def tpot_ms(self) -> float | None:
        n = len(self.token_timestamps_ns)
        if n < 2:
            return None
        span = self.token_timestamps_ns[-1] - self.token_timestamps_ns[0]
        return span / (n - 1) / _NS_PER_MS

    @property
    def decode_tps(self) -> float | None:
        n = len(self.token_timestamps_ns)
        if n < 2:
            return None
        span = self.token_timestamps_ns[-1] - self.token_timestamps_ns[0]
        if span <= 0:
            return None
        return (n - 1) / (span / _NS_PER_S)

    @property
    def total_ms(self) -> float:
        return (self.end_ns - self.request_start_ns) / _NS_PER_MS
