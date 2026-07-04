from decimal import Decimal

import pytest

from real_estate.domain.model import AlertCondition, GroupOperator, Operator, RuleGroup


def test_scalar_operator_requires_a_scalar() -> None:
    assert AlertCondition("price_per_m2", Operator.LTE, Decimal("20")).value == Decimal("20")
    with pytest.raises(ValueError):
        AlertCondition("price_per_m2", Operator.LTE, None)
    with pytest.raises(ValueError):
        AlertCondition("price_per_m2", Operator.LTE, (1, 2))


def test_between_requires_two_tuple() -> None:
    AlertCondition("area", Operator.BETWEEN, (Decimal("100"), Decimal("300")))
    with pytest.raises(ValueError):
        AlertCondition("area", Operator.BETWEEN, (Decimal("100"),))


def test_in_requires_non_empty_tuple() -> None:
    AlertCondition("province", Operator.IN, ("36", "15"))
    with pytest.raises(ValueError):
        AlertCondition("province", Operator.IN, ())


def test_exists_takes_no_value() -> None:
    AlertCondition("features.has_lift", Operator.EXISTS, None)
    with pytest.raises(ValueError):
        AlertCondition("features.has_lift", Operator.EXISTS, True)


def test_empty_field_key_rejected() -> None:
    with pytest.raises(ValueError):
        AlertCondition("  ", Operator.EQ, "x")


def test_rule_group_must_not_be_empty() -> None:
    with pytest.raises(ValueError):
        RuleGroup(GroupOperator.ALL, ())


def test_leaf_count_counts_nested_leaves() -> None:
    inner = RuleGroup(
        GroupOperator.NONE,
        (AlertCondition("description", Operator.CONTAINS, "occupied"),),
    )
    root = RuleGroup(
        GroupOperator.ALL,
        (
            AlertCondition("province", Operator.EQ, "36"),
            AlertCondition("price_per_m2", Operator.LTE, Decimal("20")),
            inner,
        ),
    )
    assert root.leaf_count() == 3
