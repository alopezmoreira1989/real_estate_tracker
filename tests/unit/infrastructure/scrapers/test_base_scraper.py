from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

import httpx
import pytest

from real_estate.domain.ports.scraper import PortalQuery, RawListing
from real_estate.infrastructure.scrapers.base import BaseScraper
from real_estate.infrastructure.scrapers.circuit_breaker import CircuitBreaker
from real_estate.infrastructure.scrapers.errors import CircuitOpenError, ScraperError
from real_estate.infrastructure.scrapers.rate_limiter import TokenBucketRateLimiter


class _FakeScraper(BaseScraper):
    portal_slug = "fake"

    def _build_url(self, query: PortalQuery) -> str:
        return "https://fake.test/search"

    def _parse(self, html: str, query: PortalQuery) -> Sequence[RawListing]:
        return [
            RawListing(
                portal_slug="fake",
                external_id="1",
                url="https://fake.test/1",
                scraped_at=datetime(2026, 7, 6, tzinfo=UTC),
                raw={"body": html},
            )
        ]


def _make_scraper(handler: object, *, max_attempts: int = 1) -> _FakeScraper:
    client = httpx.Client(transport=httpx.MockTransport(handler))  # type: ignore[arg-type]
    return _FakeScraper(
        rate_limiter=TokenBucketRateLimiter(rate_per_second=1000, burst=1000),
        circuit_breaker=CircuitBreaker(failure_threshold=2, cooldown_seconds=60),
        client=client,
        max_attempts=max_attempts,
    )


def test_fetch_returns_parsed_listings_on_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html>ok</html>")

    scraper = _make_scraper(handler)

    listings = scraper.fetch(PortalQuery(portal_slug="fake"))

    assert len(listings) == 1
    assert listings[0].external_id == "1"


def test_fetch_retries_transient_failures_then_succeeds() -> None:
    attempts = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["n"] += 1
        if attempts["n"] < 3:
            return httpx.Response(503)
        return httpx.Response(200, text="<html>ok</html>")

    scraper = _make_scraper(handler, max_attempts=5)

    listings = scraper.fetch(PortalQuery(portal_slug="fake"))

    assert attempts["n"] == 3
    assert len(listings) == 1


def test_fetch_raises_scraper_error_after_exhausting_retries() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    scraper = _make_scraper(handler, max_attempts=2)

    with pytest.raises(ScraperError):
        scraper.fetch(PortalQuery(portal_slug="fake"))


def test_repeated_failures_open_the_circuit_breaker() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    scraper = _make_scraper(handler, max_attempts=1)

    for _ in range(2):
        with pytest.raises(ScraperError):
            scraper.fetch(PortalQuery(portal_slug="fake"))

    with pytest.raises(CircuitOpenError):
        scraper.fetch(PortalQuery(portal_slug="fake"))
