"""BaseScraper — httpx client + rate limiter + tenacity retry + circuit breaker.

Composed once so every portal scraper gets politeness controls for free
(docs/architecture/06-search-scheduler.md §5, driver D7). Subclasses implement
only ``_build_url`` and ``_parse``; neither performs any cleaning, matching
``RawListing``'s contract (docs/architecture/05-normalization.md §1).
"""

from __future__ import annotations

from collections.abc import Sequence

import httpx
from tenacity import Retrying, retry_if_exception_type, stop_after_attempt, wait_exponential

from real_estate.domain.ports.scraper import PortalQuery, RawListing
from real_estate.infrastructure.scrapers.circuit_breaker import CircuitBreaker
from real_estate.infrastructure.scrapers.errors import CircuitOpenError, ScraperError
from real_estate.infrastructure.scrapers.rate_limiter import TokenBucketRateLimiter

# Identifies the bot honestly rather than impersonating a browser — polite
# scraping, not detection evasion (CLAUDE.md §14).
USER_AGENT = (
    "RealEstateAlertPlatform/0.1 (+https://github.com/alopezmoreira1989/real_estate_tracker)"
)


class BaseScraper:
    """Fetches and parses one portal's search results, politely.

    Subclasses set ``portal_slug`` and implement ``_build_url``/``_parse``.
    """

    portal_slug: str

    def __init__(
        self,
        *,
        rate_limiter: TokenBucketRateLimiter,
        circuit_breaker: CircuitBreaker,
        client: httpx.Client | None = None,
        max_attempts: int = 3,
    ) -> None:
        self._rate_limiter = rate_limiter
        self._circuit_breaker = circuit_breaker
        self._client = client or httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=10.0)
        self._max_attempts = max_attempts

    def fetch(self, query: PortalQuery) -> Sequence[RawListing]:
        if not self._circuit_breaker.allow():
            raise CircuitOpenError(f"circuit open for portal {self.portal_slug!r}")

        try:
            html = self._get(self._build_url(query))
        except Exception as exc:
            self._circuit_breaker.record_failure()
            raise ScraperError(f"fetch failed for portal {self.portal_slug!r}: {exc}") from exc

        self._circuit_breaker.record_success()
        return self._parse(html, query)

    def _get(self, url: str) -> str:
        retrying: Retrying = Retrying(
            stop=stop_after_attempt(self._max_attempts),
            wait=wait_exponential(multiplier=0.5, min=0.5, max=8),
            retry=retry_if_exception_type(httpx.HTTPError),
            reraise=True,
        )
        result: str = retrying(self._fetch_once, url)
        return result

    def _fetch_once(self, url: str) -> str:
        self._rate_limiter.acquire()
        response = self._client.get(url)
        response.raise_for_status()
        return response.text

    def _build_url(self, query: PortalQuery) -> str:
        raise NotImplementedError

    def _parse(self, html: str, query: PortalQuery) -> Sequence[RawListing]:
        raise NotImplementedError
