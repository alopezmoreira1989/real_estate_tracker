"""Selects the right Scraper for a portal — mirrors
``infrastructure/normalizers/registry.py``. No portal knowledge of its own;
portals are registered once in ``infrastructure/scrapers/__init__.py::default_registry()``.
"""

from __future__ import annotations

from real_estate.domain.ports.scraper import Scraper


class UnknownPortalError(KeyError):
    """Raised when no scraper is registered for a portal slug."""


class ScraperRegistry:
    """Looks up a :class:`Scraper` by portal slug."""

    def __init__(self) -> None:
        self._scrapers: dict[str, Scraper] = {}

    def register(self, scraper: Scraper) -> None:
        self._scrapers[scraper.portal_slug] = scraper

    def for_portal(self, portal_slug: str) -> Scraper:
        try:
            return self._scrapers[portal_slug]
        except KeyError:
            raise UnknownPortalError(f"no scraper registered for portal {portal_slug!r}") from None
