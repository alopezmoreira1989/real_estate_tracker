"""Scrapers: per-portal PortalQuery -> RawListing, plus shared politeness controls.

``default_registry()`` is the one place that lists which portals exist —
mirrors ``infrastructure/normalizers/__init__.py``. Rate limit/circuit breaker
settings come from ``PORTAL_CAPABILITIES`` (infrastructure/config), not
hardcoded here — that's the single declared source for a portal's politeness
settings (docs/architecture/06-search-scheduler.md §1).
"""

from real_estate.infrastructure.config.portal_capabilities import PORTAL_CAPABILITIES
from real_estate.infrastructure.scrapers.circuit_breaker import CircuitBreaker
from real_estate.infrastructure.scrapers.idealista import IdealistaScraper
from real_estate.infrastructure.scrapers.rate_limiter import TokenBucketRateLimiter
from real_estate.infrastructure.scrapers.registry import ScraperRegistry

__all__ = ["ScraperRegistry", "default_registry"]


def default_registry() -> ScraperRegistry:
    """Build a :class:`ScraperRegistry` with every known portal registered."""
    registry = ScraperRegistry()
    idealista_capabilities = PORTAL_CAPABILITIES["idealista"]
    registry.register(
        IdealistaScraper(
            rate_limiter=TokenBucketRateLimiter(
                rate_per_second=idealista_capabilities.rate_limit_per_second
            ),
            circuit_breaker=CircuitBreaker(
                failure_threshold=idealista_capabilities.circuit_breaker_failure_threshold,
                cooldown_seconds=idealista_capabilities.circuit_breaker_cooldown_seconds,
            ),
        )
    )
    return registry
