"""Scraper-layer exceptions.

``RunAlertCycle`` (Phase 5, #28) catches these to isolate one portal's
failure without stopping the rest of the cycle (docs/architecture/08-sequence-diagrams.md
§4, driver D7).
"""

from __future__ import annotations


class ScraperError(Exception):
    """A scrape attempt failed after retries were exhausted."""


class CircuitOpenError(ScraperError):
    """The circuit breaker is open for this portal; the request was not attempted."""
