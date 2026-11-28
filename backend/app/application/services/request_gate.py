"""Bounded admission control: at most N running requests, at most M waiting.

Bounds work inside this process only; scaling across processes arrives with workers (v2.3.x).
Lifecycle: queued -> running -> released. A request that finds the waiting room full, or
that waits longer than ``wait_timeout_s``, is rejected with ``OverloadedError``.
"""

import threading
from dataclasses import dataclass

from app.domain.exceptions import OverloadedError


@dataclass(frozen=True)
class GateConfig:
    max_concurrent: int
    max_waiting: int
    wait_timeout_s: float


class GateSlot:
    """A held slot. ``release`` is idempotent."""

    def __init__(self, gate: "RequestGate") -> None:
        self._gate = gate
        self._released = False
        self._lock = threading.Lock()

    def release(self) -> None:
        with self._lock:
            if self._released:
                return
            self._released = True
        self._gate._release()

    def __enter__(self) -> "GateSlot":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.release()


class RequestGate:
    def __init__(self, config: GateConfig) -> None:
        self._config = config
        self._cond = threading.Condition()
        self._running = 0
        self._waiting = 0

    @property
    def running(self) -> int:
        with self._cond:
            return self._running

    @property
    def waiting(self) -> int:
        with self._cond:
            return self._waiting

    def check_capacity(self) -> None:
        """Fail fast if a new request would be rejected right now (best effort)."""
        with self._cond:
            if self._running >= self._config.max_concurrent and (
                self._waiting >= self._config.max_waiting
            ):
                raise OverloadedError("server is at capacity")

    def acquire(self) -> GateSlot:
        with self._cond:
            if self._running < self._config.max_concurrent:
                self._running += 1
                return GateSlot(self)
            if self._waiting >= self._config.max_waiting:
                raise OverloadedError("server is at capacity")
            self._waiting += 1
            try:
                admitted = self._cond.wait_for(
                    lambda: self._running < self._config.max_concurrent,
                    timeout=self._config.wait_timeout_s,
                )
            finally:
                self._waiting -= 1
            if not admitted:
                raise OverloadedError("timed out waiting for capacity")
            self._running += 1
            return GateSlot(self)

    def _release(self) -> None:
        with self._cond:
            self._running -= 1
            self._cond.notify()
