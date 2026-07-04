from decimal import Decimal

import pytest

from real_estate.domain.model import Money
from real_estate.domain.vocabulary import Currency


def test_money_defaults_to_eur() -> None:
    assert Money(Decimal("100")).currency is Currency.EUR


def test_money_rejects_negative_amount() -> None:
    with pytest.raises(ValueError):
        Money(Decimal("-1"))


def test_money_rejects_non_decimal_amount() -> None:
    with pytest.raises(TypeError):
        Money(100)  # type: ignore[arg-type]


def test_money_add_and_subtract_same_currency() -> None:
    assert Money(Decimal("100")) + Money(Decimal("50")) == Money(Decimal("150"))
    assert Money(Decimal("100")) - Money(Decimal("40")) == Money(Decimal("60"))


def test_money_orders_by_amount() -> None:
    assert Money(Decimal("100")) < Money(Decimal("200"))
    assert Money(Decimal("200")) >= Money(Decimal("200"))


def test_money_is_immutable() -> None:
    m = Money(Decimal("100"))
    with pytest.raises(AttributeError):
        m.amount = Decimal("1")  # type: ignore[misc]
