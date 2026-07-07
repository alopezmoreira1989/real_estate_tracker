"""Scrapers: per-portal PortalQuery -> RawListing, plus shared politeness controls.

``default_registry()`` is the one place that lists which portals exist —
mirrors ``infrastructure/normalizers/__init__.py``.
"""

from real_estate.infrastructure.scrapers.circuit_breaker import CircuitBreaker
from real_estate.infrastructure.scrapers.idealista import IdealistaScraper
from real_estate.infrastructure.scrapers.rate_limiter import TokenBucketRateLimiter
from real_estate.infrastructure.scrapers.registry import ScraperRegistry

__all__ = ["ScraperRegistry", "default_registry"]

# Conservative defaults until a portal's real-world rate limits are tuned
# (docs/architecture/06-search-scheduler.md §5 §3 "conservative defaults now").
_DEFAULT_RATE_PER_SECOND = 0.5
_DEFAULT_CIRCUIT_FAILURE_THRESHOLD = 5
_DEFAULT_CIRCUIT_COOLDOWN_SECONDS = 60.0


def default_registry() -> ScraperRegistry:
    """Build a :class:`ScraperRegistry` with every known portal registered."""
    registry = ScraperRegistry()
    registry.register(
        IdealistaScraper(
            rate_limiter=TokenBucketRateLimiter(rate_per_second=_DEFAULT_RATE_PER_SECOND),
            circuit_breaker=CircuitBreaker(
                failure_threshold=_DEFAULT_CIRCUIT_FAILURE_THRESHOLD,
                cooldown_seconds=_DEFAULT_CIRCUIT_COOLDOWN_SECONDS,
            ),
        )
    )
    return registry
