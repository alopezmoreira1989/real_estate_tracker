from decimal import Decimal
from uuid import uuid4

import pytest

from real_estate.domain.errors import InvalidConditionError
from real_estate.domain.model import Area, Location, Money, Property, PropertyId
from real_estate.domain.model.conditions import Operator
from real_estate.domain.rules.field_registry import (
    FieldType,
    default_registry,
)
from real_estate.domain.vocabulary import ListingType, PropertyType, Province


def _prop() -> Property:
    return Property(
        id=PropertyId(uuid4()),
        listing_type=ListingType.SALE,
        property_type=PropertyType.LAND,
        location=Location(province=Province.PONTEVEDRA),
        title="Plot with water",
        price=Money(Decimal("60000")),
        area=Area(Decimal("3000")),
    )


def test_registry_extracts_primitive_values() -> None:
    reg = default_registry()
    prop = _prop()
    assert reg.get("province").extract(prop) == "36"
    assert reg.get("property_type").extract(prop) == "LAND"
    assert reg.get("price_per_m2").extract(prop) == Decimal("20")
    assert reg.get("area").extract(prop) == Decimal("3000")
    assert reg.get("rooms").extract(prop) is None
    assert reg.get("features.has_lift").extract(prop) is None


def test_unknown_field_raises_domain_error() -> None:
    with pytest.raises(InvalidConditionError):
        default_registry().get("does_not_exist")


def test_allowed_operators_match_field_type() -> None:
    reg = default_registry()
    assert reg.get("price_per_m2").field_type is FieldType.MONEY
    assert Operator.LTE in reg.get("price_per_m2").allowed_operators
    assert Operator.CONTAINS not in reg.get("price_per_m2").allowed_operators
    assert Operator.CONTAINS in reg.get("description").allowed_operators


def test_duplicate_registration_rejected() -> None:
    reg = default_registry()
    descriptor = reg.get("province")
    with pytest.raises(ValueError):
        reg.register(descriptor)
