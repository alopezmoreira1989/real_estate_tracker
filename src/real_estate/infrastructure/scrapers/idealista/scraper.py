"""IdealistaScraper — the first concrete BaseScraper (ADR-004).

``_parse`` extracts exactly the raw fields
``infrastructure/normalizers/idealista/field_map.py::IDEALISTA_FIELD_MAP``
already expects (``precio``, ``superficie``/``superficie_solar``, ``tipo``,
``operacion``, ``provincia``, ``titulo``, ``descripcion``) — the scraper and
normalizer share that vocabulary by construction. No cleaning happens here
(RawListing's contract, docs/architecture/05-normalization.md §1); values are
copied verbatim from the page, parsing/vocabulary mapping is the Normalizer's
job (Phase 4).

The card selectors (``article.item``, ``.item-price``, …) and the URL pattern
are verified against a real saved search-results page
(``tests/fixtures/idealista/search_results_page.html``) — see
``field_labels.py`` for which parts of that pattern are verified vs. inferred.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from bs4 import BeautifulSoup, Tag

from real_estate.domain.ports.scraper import PortalQuery, RawListing
from real_estate.infrastructure.scrapers.base import BaseScraper
from real_estate.infrastructure.scrapers.idealista import field_labels

_BASE_URL = "https://www.idealista.com"


class IdealistaScraper(BaseScraper):
    """Scrapes Idealista search-results pages into RawListings."""

    portal_slug = "idealista"

    def _build_url(self, query: PortalQuery) -> str:
        operation_segment = field_labels.listing_type_url_segment(query.params.get("listing_type"))
        type_segment = field_labels.property_type_url_segment(query.params.get("property_type"))
        province_slug = field_labels.province_url_slug(query.params.get("province"))

        path = f"/{operation_segment}-{type_segment}/"
        if province_slug:
            path += f"{province_slug}-{province_slug}/"
        return f"{_BASE_URL}{path}"

    def _parse(self, html: str, query: PortalQuery) -> Sequence[RawListing]:
        soup = BeautifulSoup(html, "html.parser")
        scraped_at = datetime.now(UTC)

        # Query context (property type, operation, province) isn't repeated on
        # each card — Idealista encodes it in the search URL, not per listing.
        tipo = field_labels.property_type_label(query.params.get("property_type"))
        operacion = field_labels.listing_type_label(query.params.get("listing_type"))
        provincia = field_labels.province_label(query.params.get("province"))
        is_land = query.params.get("property_type") == "LAND"

        listings = []
        for card in soup.select("article.item"):
            listing = self._parse_card(
                card,
                scraped_at,
                tipo=tipo,
                operacion=operacion,
                provincia=provincia,
                is_land=is_land,
            )
            if listing is not None:
                listings.append(listing)
        return listings

    def _parse_card(
        self,
        card: Tag,
        scraped_at: datetime,
        *,
        tipo: str,
        operacion: str,
        provincia: str,
        is_land: bool,
    ) -> RawListing | None:
        external_id = card.get("data-element-id")
        if not isinstance(external_id, str) or not external_id:
            return None

        link = card.select_one("a.item-link")
        title = ""
        url = ""
        if link is not None:
            title_attr = link.get("title")
            title = title_attr if isinstance(title_attr, str) else link.get_text(strip=True)
            href = link.get("href")
            url = href if isinstance(href, str) else ""

        raw: dict[str, Any] = {
            "titulo": title,
            "tipo": tipo,
            "operacion": operacion,
            "provincia": provincia,
        }

        description_el = card.select_one(".item-description p")
        if description_el is not None:
            raw["descripcion"] = description_el.get_text(strip=True)

        price_el = card.select_one(".item-price")
        if price_el is not None:
            raw["precio"] = price_el.get_text(strip=True)

        # Only a single size figure is verified on a real card (land plot
        # size). Flat/house cards likely also show rooms/bathrooms alongside
        # it, but that markup hasn't been observed on a real page yet.
        size_el = card.select_one(".item-detail-char .item-detail")
        if size_el is not None:
            size_field = "superficie_solar" if is_land else "superficie"
            raw[size_field] = size_el.get_text(strip=True)

        return RawListing(
            portal_slug=self.portal_slug,
            external_id=external_id,
            url=url,
            scraped_at=scraped_at,
            raw=raw,
        )
