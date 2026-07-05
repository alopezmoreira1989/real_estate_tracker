from decimal import Decimal
from uuid import uuid4

import pytest

from real_estate.domain.model import (
    Area,
    Location,
    Money,
    Property,
    PropertyId,
)
from real_estate.domain.vocabulary import LandType, ListingType, PropertyType, Province


def _land(**overrides: object) -> Property:
    base: dict[str, object] = dict(
        id=PropertyId(uuid4()),
        listing_type=ListingType.SALE,
        property_type=PropertyType.LAND,
        location=Location(province=Province.PONTEVEDRA),
        title="Urbanizable plot",
    )
    base.update(overrides)
    return Property(**base)  # type: ignore[arg-type]


def test_price_per_m2_is_derived() -> None:
    prop = _land(price=Money(Decimal("60000")), area=Area(Decimal("3000")))
    ppm2 = prop.price_per_m2
    assert ppm2 is not None
    assert ppm2.amount == Decimal("20")


def test_price_per_m2_is_none_without_price_or_area() -> None:
    assert _land(area=Area(Decimal("3000"))).price_per_m2 is None
    assert _land(price=Money(Decimal("60000"))).price_per_m2 is None


def test_land_type_allowed_only_for_land() -> None:
    _land(land_type=LandType.URBANIZABLE)  # ok
    with pytest.raises(ValueError):
        Property(
            id=PropertyId(uuid4()),
            listing_type=ListingType.SALE,
            property_type=PropertyType.FLAT,
            location=Location(province=Province.MADRID),
            title="Flat",
            land_type=LandType.URBAN,
        )


def test_negative_rooms_rejected() -> None:
    with pytest.raises(ValueError):
        _land(rooms=-1)
