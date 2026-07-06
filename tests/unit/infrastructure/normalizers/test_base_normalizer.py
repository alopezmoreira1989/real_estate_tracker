from datetime import UTC, datetime
from decimal import Decimal

from real_estate.domain.ports.scraper import RawListing
from real_estate.domain.vocabulary import LandType, ListingType, PropertyType, Province
from real_estate.infrastructure.normalizers.base import BaseNormalizer


class _FakeNormalizer(BaseNormalizer):
    portal_slug = "fake"
    field_map = {
        "precio": "price",
        "tamano": "area",
        "tipo": "property_type",
        "tipo_suelo": "land_type",
        "operacion": "listing_type",
        "provincia": "province",
        "titulo": "title",
        "ascensor": "features.has_lift",
        "fotos": "media.images",
    }


def _raw(payload: dict[str, object]) -> RawListing:
    return RawListing(
        portal_slug="fake",
        external_id="1",
        url="https://example.com/1",
        scraped_at=datetime(2026, 7, 6, tzinfo=UTC),
        raw=payload,
    )


def test_normalizes_a_clean_listing() -> None:
    result = _FakeNormalizer().normalize(
        _raw(
            {
                "precio": "120.000 €",
                "tamano": "85 m²",
                "tipo": "Piso",
                "operacion": "Venta",
                "provincia": "Pontevedra",
                "titulo": "Piso luminoso",
                "ascensor": "Sí",
                "fotos": ["https://img.example.com/1.jpg"],
            }
        )
    )

    assert result.issues == ()
    prop = result.property
    assert prop is not None
    assert prop.property_type is PropertyType.FLAT
    assert prop.listing_type is ListingType.SALE
    assert prop.location.province is Province.PONTEVEDRA
    assert prop.features.has_lift is True
    assert prop.media.images == ("https://img.example.com/1.jpg",)
    assert prop.price is not None
    assert prop.price.amount == Decimal("120000")
    assert prop.area is not None
    assert prop.area.square_meters == Decimal("85")


def test_same_raw_listing_normalizes_to_the_same_property_id() -> None:
    raw = _raw({"tipo": "Piso", "provincia": "Pontevedra", "operacion": "Venta"})

    first = _FakeNormalizer().normalize(raw).property
    second = _FakeNormalizer().normalize(raw).property

    assert first is not None
    assert second is not None
    assert first.id == second.id


def test_land_type_resolved_when_property_type_is_land() -> None:
    result = _FakeNormalizer().normalize(
        _raw(
            {
                "tipo": "Suelo",
                "tipo_suelo": "Suelo urbanizable",
                "provincia": "Pontevedra",
                "operacion": "Venta",
            }
        )
    )

    assert result.property is not None
    assert result.property.land_type is LandType.URBANIZABLE


def test_land_type_is_none_when_property_type_is_not_land() -> None:
    result = _FakeNormalizer().normalize(
        _raw({"tipo": "Piso", "provincia": "Pontevedra", "operacion": "Venta"})
    )

    assert result.property is not None
    assert result.property.land_type is None


def test_unmapped_property_type_falls_back_and_emits_issue() -> None:
    result = _FakeNormalizer().normalize(
        _raw({"tipo": "Yurta", "provincia": "Lugo", "operacion": "Venta"})
    )

    assert result.property is not None
    assert result.property.property_type is PropertyType.OTHER
    assert any(issue.field == "property_type" for issue in result.issues)


def test_unparseable_price_falls_back_to_none_and_emits_issue() -> None:
    result = _FakeNormalizer().normalize(
        _raw({"precio": "Consultar", "tipo": "Piso", "provincia": "Lugo", "operacion": "Venta"})
    )

    assert result.property is not None
    assert result.property.price is None
    assert any(issue.field == "price" for issue in result.issues)


def test_invalid_media_url_is_dropped_with_an_issue() -> None:
    result = _FakeNormalizer().normalize(
        _raw(
            {
                "tipo": "Piso",
                "provincia": "Lugo",
                "operacion": "Venta",
                "fotos": ["not-a-url"],
            }
        )
    )

    assert result.property is not None
    assert result.property.media.images == ()
    assert any(issue.field == "images" for issue in result.issues)


def test_missing_fields_default_gracefully() -> None:
    result = _FakeNormalizer().normalize(_raw({}))

    assert result.property is not None
    prop = result.property
    assert prop.property_type is PropertyType.OTHER
    assert prop.listing_type is ListingType.OTHER
    assert prop.location.province is Province.UNKNOWN
    assert prop.title == ""
