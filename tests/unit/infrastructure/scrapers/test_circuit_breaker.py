import threading

import pytest

from real_estate.infrastructure.scrapers.circuit_breaker import CircuitBreaker, CircuitState


class _FakeClock:
    def __init__(self, start: float = 0.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def test_starts_closed_and_allows_requests() -> None:
    breaker = CircuitBreaker(failure_threshold=3, cooldown_seconds=10)

    assert breaker.allow() is True
    assert breaker.state is CircuitState.CLOSED


def test_opens_after_consecutive_failures_reach_threshold() -> None:
    breaker = CircuitBreaker(failure_threshold=2, cooldown_seconds=10)

    breaker.record_failure()
    assert breaker.allow() is True

    breaker.record_failure()
    assert breaker.allow() is False
    assert breaker.state is CircuitState.OPEN


def test_success_resets_the_consecutive_failure_count() -> None:
    breaker = CircuitBreaker(failure_threshold=2, cooldown_seconds=10)

    breaker.record_failure()
    breaker.record_success()
    breaker.record_failure()

    assert breaker.allow() is True


def test_half_opens_after_cooldown_and_allows_one_attempt() -> None:
    clock = _FakeClock()
    breaker = CircuitBreaker(failure_threshold=1, cooldown_seconds=5, clock=clock)
    breaker.record_failure()
    assert breaker.allow() is False

    clock.advance(5)

    assert breaker.state is CircuitState.HALF_OPEN
    assert breaker.allow() is True


def test_failure_during_half_open_reopens_the_circuit() -> None:
    clock = _FakeClock()
    breaker = CircuitBreaker(failure_threshold=1, cooldown_seconds=5, clock=clock)
    breaker.record_failure()
    clock.advance(5)
    assert breaker.state is CircuitState.HALF_OPEN

    breaker.record_failure()

    assert breaker.state is CircuitState.OPEN


def test_rejects_invalid_thresholds() -> None:
    with pytest.raises(ValueError):
        CircuitBreaker(failure_threshold=0, cooldown_seconds=5)
    with pytest.raises(ValueError):
        CircuitBreaker(failure_threshold=1, cooldown_seconds=0)


def test_concurrent_record_failure_never_exceeds_the_threshold_count() -> None:
    """Shared by every worker scraping one portal (#33's worker pool) — a
    torn read/write on ``_consecutive_failures`` would let it under- or
    over-count under concurrency; a lock makes each increment atomic."""
    breaker = CircuitBreaker(failure_threshold=1000, cooldown_seconds=10)
    threads = [threading.Thread(target=breaker.record_failure) for _ in range(200)]

    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert breaker._consecutive_failures == 200  # noqa: SLF001
