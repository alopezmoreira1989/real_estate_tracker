from decimal import Decimal

import pytest

from real_estate.domain.model import Area, Money, PricePerM2
from real_estate.domain.vocabulary import Currency


def test_area_must_be_positive() -> None:
    with pytest.raises(ValueError):
        Area(Decimal("0"))


def test_area_orders_by_value() -> None:
    assert Area(Decimal("100")) < Area(Decimal("3000"))


def test_price_per_m2_is_computed_from_price_and_area() -> None:
    ppm2 = PricePerM2.from_price_and_area(Money(Decimal("60000")), Area(Decimal("3000")))
    assert ppm2.amount == Decimal("20")
    assert ppm2.currency is Currency.EUR


def test_price_per_m2_must_be_positive() -> None:
    with pytest.raises(ValueError):
        PricePerM2(Decimal("0"))


def test_price_per_m2_orders_by_amount() -> None:
    assert PricePerM2(Decimal("20")) <= PricePerM2(Decimal("25"))
