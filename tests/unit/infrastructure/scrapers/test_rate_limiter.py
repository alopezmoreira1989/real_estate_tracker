import pytest

from real_estate.infrastructure.scrapers.rate_limiter import TokenBucketRateLimiter


class _FakeClock:
    def __init__(self, start: float = 0.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def test_acquire_does_not_sleep_when_a_token_is_available() -> None:
    clock = _FakeClock()
    sleeps: list[float] = []
    limiter = TokenBucketRateLimiter(rate_per_second=2, burst=2, clock=clock, sleep=sleeps.append)

    limiter.acquire()

    assert sleeps == []


def test_acquire_sleeps_until_a_token_refills_once_burst_is_exhausted() -> None:
    clock = _FakeClock()
    sleeps: list[float] = []

    def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)
        clock.advance(seconds)

    limiter = TokenBucketRateLimiter(rate_per_second=2, burst=1, clock=clock, sleep=fake_sleep)

    limiter.acquire()  # consumes the single burst token
    limiter.acquire()  # must wait for a refill

    assert sleeps == [0.5]  # 1 token needed / 2 tokens per second = 0.5s


def test_rejects_non_positive_rate() -> None:
    with pytest.raises(ValueError):
        TokenBucketRateLimiter(rate_per_second=0)
