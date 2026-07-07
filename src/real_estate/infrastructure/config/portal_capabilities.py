"""Declarative per-portal capabilities.

States which canonical fields a portal can filter **server-side** (pushable —
used by the SearchPlanner, application layer, to build the coarse portal
query) and its politeness settings (rate limit, circuit breaker) — read by
whoever wires up a scraper, never hardcoded in the planner or the scraper
itself (docs/architecture/03-database.md `portal.capabilities`,
docs/architecture/06-search-scheduler.md §1).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PortalCapabilities:
    """What a portal supports, declared once per portal."""

    portal_slug: str
    pushable_fields: frozenset[str]
    rate_limit_per_second: float
    circuit_breaker_failure_threshold: int
    circuit_breaker_cooldown_seconds: float


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
    ),
}
