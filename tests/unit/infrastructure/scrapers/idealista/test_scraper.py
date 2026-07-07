"""Contract test against a real saved Idealista search-results page
(tests/fixtures/idealista/search_results_page.html — "71 terrenos en
Pontevedra"). Proves the HTML -> RawListing step against real markup, not
just against our own assumptions about it (see the Phase 5 plan / ADR-004).
"""

from __future__ import annotations

from pathlib import Path

import httpx

from real_estate.domain.ports.scraper import PortalQuery
from real_estate.infrastructure.scrapers.circuit_breaker import CircuitBreaker
from real_estate.infrastructure.scrapers.idealista import IdealistaScraper
from real_estate.infrastructure.scrapers.rate_limiter import TokenBucketRateLimiter

_FIXTURE = (
    Path(__file__).resolve().parents[4] / "fixtures" / "idealista" / "search_results_page.html"
)

_LAND_PONTEVEDRA_QUERY = PortalQuery(
    portal_slug="idealista",
    params={"property_type": "LAND", "listing_type": "SALE", "province": "36"},
)


def _make_scraper() -> IdealistaScraper:
    return IdealistaScraper(
        rate_limiter=TokenBucketRateLimiter(rate_per_second=1000, burst=1000),
        circuit_breaker=CircuitBreaker(failure_threshold=5, cooldown_seconds=60),
    )


def test_build_url_matches_the_real_pages_canonical_url() -> None:
    scraper = _make_scraper()

    url = scraper._build_url(_LAND_PONTEVEDRA_QUERY)  # noqa: SLF001

    assert url == "https://www.idealista.com/venta-terrenos/pontevedra-pontevedra/"


def test_parse_extracts_every_real_listing_card() -> None:
    html = _FIXTURE.read_text(encoding="utf-8")
    scraper = _make_scraper()

    listings = scraper._parse(html, _LAND_PONTEVEDRA_QUERY)  # noqa: SLF001

    assert len(listings) == 30  # verified count of article.item cards, excludes 2 ad cards


def test_parse_extracts_sane_raw_fields_for_a_known_listing() -> None:
    html = _FIXTURE.read_text(encoding="utf-8")
    scraper = _make_scraper()

    listings = scraper._parse(html, _LAND_PONTEVEDRA_QUERY)  # noqa: SLF001
    by_id = {listing.external_id: listing for listing in listings}

    listing = by_id["100338209"]
    assert listing.portal_slug == "idealista"
    assert listing.url == "https://www.idealista.com/inmueble/100338209/"
    assert "Estrigueiras" in listing.raw["titulo"]
    assert listing.raw["precio"] == "688.590€"
    assert listing.raw["superficie"] == "15.677 m²"
    assert listing.raw["tipo"] == "Suelo"
    assert listing.raw["operacion"] == "Venta"
    assert listing.raw["provincia"] == "Pontevedra"
    assert "descripcion" in listing.raw


def test_parse_never_includes_ad_cards() -> None:
    html = _FIXTURE.read_text(encoding="utf-8")
    scraper = _make_scraper()

    listings = scraper._parse(html, _LAND_PONTEVEDRA_QUERY)  # noqa: SLF001

    # every real card has a numeric external_id; an ad slot never does
    assert all(listing.external_id.isdigit() for listing in listings)


def test_fetch_end_to_end_against_the_real_fixture_via_mock_transport() -> None:
    html = _FIXTURE.read_text(encoding="utf-8")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/venta-terrenos/pontevedra-pontevedra/"
        return httpx.Response(200, text=html)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    scraper = IdealistaScraper(
        rate_limiter=TokenBucketRateLimiter(rate_per_second=1000, burst=1000),
        circuit_breaker=CircuitBreaker(failure_threshold=5, cooldown_seconds=60),
        client=client,
    )

    listings = scraper.fetch(_LAND_PONTEVEDRA_QUERY)

    assert len(listings) == 30
