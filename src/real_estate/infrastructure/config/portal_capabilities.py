"""Declarative per-portal capabilities: the concrete data.

States which canonical fields a portal can filter **server-side** (pushable —
used by the SearchPlanner, application layer, to build the coarse portal
query) and its politeness settings (rate limit, circuit breaker) — read by
whoever wires up a scraper, never hardcoded in the planner or the scraper
itself (docs/architecture/03-database.md `portal.capabilities`,
docs/architecture/06-search-scheduler.md §1).

The ``PortalCapabilities`` *shape* lives in ``application/ports.py`` (not
here) so application services can depend on it without importing
infrastructure — see that module's docstring.
"""

from __future__ import annotations

from real_estate.application.ports import PortalCapabilities

PORTAL_CAPABILITIES: dict[str, PortalCapabilities] = {
    "idealista": PortalCapabilities(
        portal_slug="idealista",
        # Matches the URL filters IdealistaScraper._build_url actually supports
        # (infrastructure/scrapers/idealista/field_labels.py) — province,
        # property type, and operation are single-value URL segments; price is
        # exposed as a coarse min/max range.
        pushable_fields=frozenset({"province", "property_type", "listing_type", "price"}),
        # Conservative defaults until tuned against real-world behavior
        # (docs/architecture/06-search-scheduler.md §3).
        rate_limit_per_second=0.5,
        circuit_breaker_failure_threshold=5,
        circuit_breaker_cooldown_seconds=60.0,
        # Explicit (not just relying on the default): kept at 1 until
        # Idealista's real-world tolerance for concurrent requests is known
        # (docs/architecture/06-search-scheduler.md §5-§6).
        max_concurrency=1,
    ),
}
