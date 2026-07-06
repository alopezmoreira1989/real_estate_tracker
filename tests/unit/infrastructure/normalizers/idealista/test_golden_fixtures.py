"""Golden-fixture tests: recorded RawListing payloads -> exact Property output.

Each fixture doubles as a regression test — a change to the Idealista field
map, parsers, or vocabularies that alters the result surfaces here
(CLAUDE.md §8).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from real_estate.domain.ports.scraper import RawListing
from real_estate.domain.vocabulary import ListingType, PropertyType, Province
from real_estate.infrastructure.normalizers.idealista import IdealistaNormalizer

_FIXTURES_DIR = Path(__file__).resolve().parents[4] / "fixtures" / "idealista"


def _load(name: str) -> RawListing:
    payload = json.loads((_FIXTURES_DIR / name).read_text(encoding="utf-8"))
    return RawListing(
        portal_slug="idealista",
        external_id=payload["external_id"],
        url=payload["url"],
        scraped_at=datetime(2026, 7, 6, tzinfo=UTC),
        raw=payload["raw"],
    )


def test_clean_flat_normalizes_with_no_issues() -> None:
    result = IdealistaNormalizer().normalize(_load("clean_flat.json"))

    assert result.issues == ()
    prop = result.property
    assert prop is not None
    assert prop.property_type is PropertyType.FLAT
    assert prop.listing_type is ListingType.SALE
    assert prop.location.province is Province.PONTEVEDRA
    assert prop.title == "Piso reformado en el centro"
    assert prop.rooms == 3
    assert prop.bathrooms == 2
    assert prop.price is not None
    assert prop.price.amount == Decimal("185000")
    assert prop.area is not None
    assert prop.area.square_meters == Decimal("90")
    assert prop.price_per_m2 is not None
    assert prop.features.has_lift is True
    assert prop.features.has_terrace is True
    assert prop.features.has_garden is False
    assert prop.media.images == (
        "https://img.idealista.com/11111111/1.jpg",
        "https://img.idealista.com/11111111/2.jpg",
    )


def test_missing_and_unparseable_fields_degrade_to_none_with_issues() -> None:
    result = IdealistaNormalizer().normalize(_load("missing_fields.json"))

    prop = result.property
    assert prop is not None
    assert prop.price is None
    assert prop.area is None
    assert prop.rooms is None
    assert prop.bathrooms is None  # absent from the raw payload entirely
    assert prop.property_type is PropertyType.FLAT
    assert prop.location.province is Province.LUGO

    issue_fields = {issue.field for issue in result.issues}
    assert issue_fields == {"price", "area", "rooms"}


def test_unmapped_vocabulary_falls_back_to_other_and_unknown_with_issues() -> None:
    result = IdealistaNormalizer().normalize(_load("unmapped_vocabulary.json"))

    prop = result.property
    assert prop is not None
    assert prop.property_type is PropertyType.OTHER
    assert prop.location.province is Province.UNKNOWN
    # still parses everything that *was* mappable — never drops the listing
    assert prop.price is not None
    assert prop.price.amount == Decimal("50000")

    issue_fields = {issue.field for issue in result.issues}
    assert issue_fields == {"property_type", "province"}
