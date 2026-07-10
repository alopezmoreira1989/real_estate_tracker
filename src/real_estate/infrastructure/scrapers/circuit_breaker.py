"""Circuit breaker — pauses a failing portal without affecting others.

Opens after ``failure_threshold`` consecutive failures; half-opens after
``cooldown_seconds`` to test whether the portal has recovered (driver D7,
docs/architecture/06-search-scheduler.md §5). One instance is shared by every
concurrent worker scraping a given portal (#33's per-portal worker pool), so
its mutable state is guarded by a lock rather than assumed single-threaded.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from enum import Enum, auto


class CircuitState(Enum):
    CLOSED = auto()
    OPEN = auto()
    HALF_OPEN = auto()


class CircuitBreaker:
    """Tracks consecutive failures for one portal and gates further attempts."""

    def __init__(
        self,
        failure_threshold: int,
        cooldown_seconds: float,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if failure_threshold < 1:
            raise ValueError("failure_threshold must be >= 1")
        if cooldown_seconds <= 0:
            raise ValueError("cooldown_seconds must be positive")
        self._threshold = failure_threshold
        self._cooldown = cooldown_seconds
        self._clock = clock
        self._state = CircuitState.CLOSED
        self._consecutive_failures = 0
        self._opened_at: float | None = None
        self._lock = threading.Lock()

    @property
    def state(self) -> CircuitState:
        with self._lock:
            return self._state_locked()

    def _state_locked(self) -> CircuitState:
        if (
            self._state is CircuitState.OPEN
            and self._opened_at is not None
            and self._clock() - self._opened_at >= self._cooldown
        ):
            self._state = CircuitState.HALF_OPEN
        return self._state

    def allow(self) -> bool:
        """Whether a request may be attempted right now."""
        with self._lock:
            return self._state_locked() is not CircuitState.OPEN

    def record_success(self) -> None:
        with self._lock:
            self._consecutive_failures = 0
            self._state = CircuitState.CLOSED
            self._opened_at = None

    def record_failure(self) -> None:
        with self._lock:
            self._consecutive_failures += 1
            if self._consecutive_failures >= self._threshold:
                self._state = CircuitState.OPEN
                self._opened_at = self._clock()
