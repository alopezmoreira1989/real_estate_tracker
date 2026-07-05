from real_estate.domain.vocabulary import (
    Currency,
    LandType,
    ListingStatus,
    ListingType,
    PropertyType,
)


def test_currency_defaults_include_eur() -> None:
    assert Currency.EUR == "EUR"


def test_listing_type_has_never_drop_other() -> None:
    assert "OTHER" in ListingType.__members__
    assert ListingType.SALE == "SALE"


def test_listing_status_has_unknown_fallback() -> None:
    assert ListingStatus.UNKNOWN == "UNKNOWN"


def test_property_type_has_other_fallback_and_core_members() -> None:
    assert PropertyType.OTHER == "OTHER"
    for member in ("FLAT", "HOUSE", "LAND", "GARAGE"):
        assert member in PropertyType.__members__


def test_land_type_has_unknown_and_urbanizable() -> None:
    assert LandType.URBANIZABLE == "URBANIZABLE"
    assert LandType.UNKNOWN == "UNKNOWN"
