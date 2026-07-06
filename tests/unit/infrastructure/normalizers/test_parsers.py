from decimal import Decimal

from real_estate.domain.model.area import Area
from real_estate.domain.model.money import Money
from real_estate.domain.vocabulary import Currency
from real_estate.infrastructure.normalizers.parsers import parse_area, parse_int, parse_money


def test_parse_money_handles_spanish_thousands_separator() -> None:
    assert parse_money("120.000 €") == Money(Decimal("120000"), Currency.EUR)


def test_parse_money_handles_spanish_decimal_comma() -> None:
    assert parse_money("1.234,56 €") == Money(Decimal("1234.56"), Currency.EUR)


def test_parse_money_returns_none_for_missing_or_unparseable() -> None:
    assert parse_money(None) is None
    assert parse_money("") is None
    assert parse_money("Consultar precio") is None


def test_parse_money_returns_none_for_negative_amount() -> None:
    assert parse_money("-50 €") is None


def test_parse_area_handles_thousands_and_unit_suffix() -> None:
    assert parse_area("3.000 m²") == Area(Decimal("3000"))


def test_parse_area_handles_decimal_comma() -> None:
    assert parse_area("85,5 m²") == Area(Decimal("85.5"))


def test_parse_area_returns_none_for_non_positive_or_missing() -> None:
    assert parse_area("0 m²") is None
    assert parse_area(None) is None
    assert parse_area("N/D") is None


def test_parse_int_extracts_leading_digits() -> None:
    assert parse_int("3 habitaciones") == 3
    assert parse_int("120") == 120


def test_parse_int_returns_none_for_missing_or_unparseable() -> None:
    assert parse_int(None) is None
    assert parse_int("N/D") is None
