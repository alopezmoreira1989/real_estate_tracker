"""Token-bucket rate limiter — enforces a per-portal requests/second budget.

Politeness is a correctness feature, not optional (CLAUDE.md §14,
docs/architecture/06-search-scheduler.md §5). MVP is single-threaded/sequential
(no worker pool yet — that's Phase 7), but the limiter is thread-safe so it can
be shared once one exists.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable


class TokenBucketRateLimiter:
    """Blocks the caller in :meth:`acquire` until a token is available."""

    def __init__(
        self,
        rate_per_second: float,
        *,
        burst: int | None = None,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if rate_per_second <= 0:
            raise ValueError("rate_per_second must be positive")
        self._rate = rate_per_second
        self._capacity = float(burst if burst is not None else max(1, round(rate_per_second)))
        self._tokens = self._capacity
        self._clock = clock
        self._sleep = sleep
        self._last_refill = clock()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        """Block until one token is available, then consume it."""
        with self._lock:
            self._refill()
            if self._tokens < 1:
                wait_seconds = (1 - self._tokens) / self._rate
                self._sleep(wait_seconds)
                self._refill()
            self._tokens -= 1

    def _refill(self) -> None:
        now = self._clock()
        elapsed = now - self._last_refill
        self._last_refill = now
        self._tokens = min(self._capacity, self._tokens + elapsed * self._rate)
