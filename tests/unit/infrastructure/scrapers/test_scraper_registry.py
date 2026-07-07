from __future__ import annotations

from collections.abc import Sequence

import pytest

from real_estate.domain.ports.scraper import PortalQuery, RawListing
from real_estate.infrastructure.scrapers.registry import ScraperRegistry, UnknownPortalError


class _FakeScraper:
    portal_slug = "fake"

    def fetch(self, query: PortalQuery) -> Sequence[RawListing]:
        return []


def test_register_and_lookup_by_portal_slug() -> None:
    registry = ScraperRegistry()
    scraper = _FakeScraper()

    registry.register(scraper)

    assert registry.for_portal("fake") is scraper


def test_unknown_portal_raises() -> None:
    registry = ScraperRegistry()

    with pytest.raises(UnknownPortalError):
        registry.for_portal("nonexistent")
