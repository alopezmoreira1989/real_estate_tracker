from decimal import Decimal

import pytest

from real_estate.domain.model.conditions import Operator
from real_estate.domain.rules.operators import strategy_for


@pytest.mark.parametrize(
    ("operator", "actual", "expected", "result"),
    [
        (Operator.EQ, "LAND", "LAND", True),
        (Operator.EQ, "FLAT", "LAND", False),
        (Operator.NEQ, "FLAT", "LAND", True),
        (Operator.LT, Decimal("10"), Decimal("20"), True),
        (Operator.LTE, Decimal("20"), Decimal("20"), True),
        (Operator.GT, Decimal("30"), Decimal("20"), True),
        (Operator.GTE, Decimal("3000"), Decimal("3000"), True),
        (Operator.BETWEEN, Decimal("15"), (Decimal("10"), Decimal("20")), True),
        (Operator.BETWEEN, Decimal("25"), (Decimal("10"), Decimal("20")), False),
        (Operator.IN, "36", ("36", "15"), True),
        (Operator.IN, "28", ("36", "15"), False),
        (Operator.NOT_IN, "28", ("36", "15"), True),
    ],
)
def test_operator_truth_values(
    operator: Operator, actual: object, expected: object, result: bool
) -> None:
    assert strategy_for(operator).matches(actual, expected) is result


def test_contains_folds_case_and_accents() -> None:
    contains = strategy_for(Operator.CONTAINS)
    assert contains.matches("Terreno con AGUA y luz", "agua") is True
    assert contains.matches("parcela con água", "AGUA") is True
    assert contains.matches("sin nada", "agua") is False


def test_not_contains() -> None:
    not_contains = strategy_for(Operator.NOT_CONTAINS)
    assert not_contains.matches("piso ocupado", "okupado") is True
    assert not_contains.matches("piso ocupado", "ocupado") is False


def test_exists_and_not_exists() -> None:
    assert strategy_for(Operator.EXISTS).matches(True, None) is True
    assert strategy_for(Operator.EXISTS).matches(None, None) is False
    assert strategy_for(Operator.NOT_EXISTS).matches(None, None) is True
    assert strategy_for(Operator.NOT_EXISTS).matches(False, None) is False


@pytest.mark.parametrize(
    "operator",
    [Operator.EQ, Operator.LT, Operator.GTE, Operator.BETWEEN, Operator.IN, Operator.CONTAINS],
)
def test_none_actual_fails_positive_comparisons(operator: Operator) -> None:
    expected = (Decimal("1"), Decimal("2")) if operator is Operator.BETWEEN else "x"
    if operator is Operator.IN:
        expected = ("x", "y")
    assert strategy_for(operator).matches(None, expected) is False
