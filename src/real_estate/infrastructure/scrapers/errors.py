"""Scraper-layer exceptions.

``RunAlertCycle`` (Phase 5, #28) catches these to isolate one portal's
failure without stopping the rest of the cycle (docs/architecture/08-sequence-diagrams.md
§4, driver D7). ``ScraperError`` itself is defined on the domain port
(``domain/ports/scraper.py``) so the application layer can catch it without
depending on infrastructure; re-exported here since every scraper adapter's
own code reaches for it via this module.
"""

from __future__ import annotations

from real_estate.domain.ports.scraper import ScraperError

__all__ = ["CircuitOpenError", "ScraperError"]


class CircuitOpenError(ScraperError):
    """The circuit breaker is open for this portal; the request was not attempted."""
