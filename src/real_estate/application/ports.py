"""Application-level ports and shared value shapes.

Used by use-cases/services but not owned by the domain — e.g. ``Clock`` (an
application-level dependency, not a domain concept) and
``PortalCapabilities`` (a plain data shape: infrastructure holds the
concrete per-portal values, but application services like ``SearchPlanner``
need the *shape* without importing infrastructure directly — infrastructure
may depend on application, never the reverse, CLAUDE.md §6).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


class Clock(Protocol):
    """Injected time source — no ``datetime.now()`` in use-case logic
    (CLAUDE.md §8), so a cycle's timestamps are deterministic and testable.
    """

    def now(self) -> datetime: ...


@dataclass(frozen=True, slots=True)
class PortalCapabilities:
    """What a portal supports: which canonical fields it can filter
    server-side (pushable), and its politeness settings.
    """

    portal_slug: str
    pushable_fields: frozenset[str]
    rate_limit_per_second: float
    circuit_breaker_failure_threshold: int
    circuit_breaker_cooldown_seconds: float
