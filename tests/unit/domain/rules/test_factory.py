from decimal import Decimal
from uuid import uuid4

import pytest

from real_estate.domain.errors import InvalidConditionError
from real_estate.domain.model import (
    Area,
    Location,
    Money,
    Property,
    PropertyId,
)
from real_estate.domain.model.conditions import (
    AlertCondition,
    GroupOperator,
    Operator,
    RuleGroup,
)
from real_estate.domain.rules import SpecificationFactory, default_registry
from real_estate.domain.vocabulary import ListingType, PropertyType, Province


def _factory() -> SpecificationFactory:
    return SpecificationFactory(default_registry())


def _prop(**overrides: object) -> Property:
    base: dict[str, object] = dict(
        id=PropertyId(uuid4()),
        listing_type=ListingType.SALE,
        property_type=PropertyType.LAND,
        location=Location(province=Province.PONTEVEDRA),
        title="Plot",
        price=Money(Decimal("60000")),
        area=Area(Decimal("3000")),
    )
    base.update(overrides)
    return Property(**base)  # type: ignore[arg-type]


def test_factory_builds_evaluable_specification() -> None:
    conditions = RuleGroup(
        GroupOperator.ALL,
        (
            AlertCondition("province", Operator.EQ, "36"),
            AlertCondition("price_per_m2", Operator.LTE, Decimal("20")),
        ),
    )
    spec = _factory()._node(conditions)
    assert spec.is_satisfied_by(_prop()) is True
    # price/m2 = 60000 / 1000 = 60 > 20 -> fails
    assert spec.is_satisfied_by(_prop(area=Area(Decimal("1000")))) is False


def test_unknown_field_raises() -> None:
    conditions = RuleGroup(GroupOperator.ALL, (AlertCondition("nope", Operator.EQ, "x"),))
    with pytest.raises(InvalidConditionError):
        _factory()._node(conditions)


def test_operator_not_allowed_for_field_raises() -> None:
    # CONTAINS is invalid on a numeric field
    conditions = RuleGroup(
        GroupOperator.ALL,
        (AlertCondition("price_per_m2", Operator.CONTAINS, "2"),),
    )
    with pytest.raises(InvalidConditionError):
        _factory()._node(conditions)
