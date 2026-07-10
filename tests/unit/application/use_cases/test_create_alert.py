from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from types import TracebackType
from uuid import uuid4

import pytest

from real_estate.application.use_cases.create_alert import CreateAlert
from real_estate.domain.errors import InvalidConditionError
from real_estate.domain.model.alert import SearchAlert
from real_estate.domain.model.conditions import Operator
from real_estate.domain.model.identifiers import UserId
from real_estate.domain.rules import default_registry

NOW = datetime(2026, 7, 9, 12, 0)


@dataclass
class _FixedClock:
    _now: datetime

    def now(self) -> datetime:
        return self._now


class _FakeAlertRepo:
    def __init__(self) -> None:
        self.added: list[SearchAlert] = []

    def add(self, alert: SearchAlert) -> None:
        self.added.append(alert)


class _FakeUoW:
    def __init__(self) -> None:
        self.alerts = _FakeAlertRepo()
        self.committed = False

    def __enter__(self) -> _FakeUoW:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        return None

    def commit(self) -> None:
        self.committed = True


def _make_create_alert() -> tuple[CreateAlert, _FakeUoW]:
    uow = _FakeUoW()
    use_case = CreateAlert(
        uow_factory=lambda: uow, field_registry=default_registry(), clock=_FixedClock(NOW)
    )
    return use_case, uow


def test_parses_a_simple_eq_condition_and_persists_the_alert() -> None:
    use_case, uow = _make_create_alert()

    alert = use_case.run(
        user_id=UserId(uuid4()),
        name="Land in Pontevedra",
        portal_slugs=frozenset({"idealista"}),
        frequency_seconds=900,
        condition_strings=["province:EQ:36"],
    )

    assert uow.committed is True
    assert uow.alerts.added == [alert]
    [condition] = alert.conditions.children
    assert condition.field_key == "province"
    assert condition.operator is Operator.EQ
    assert condition.value == "36"


def test_coerces_money_fields_to_decimal() -> None:
    use_case, _ = _make_create_alert()

    alert = use_case.run(
        user_id=UserId(uuid4()),
        name="Cheap land",
        portal_slugs=frozenset({"idealista"}),
        frequency_seconds=900,
        condition_strings=["price_per_m2:LTE:20"],
    )

    [condition] = alert.conditions.children
    assert condition.value == Decimal("20")


def test_parses_a_between_condition_into_a_tuple() -> None:
    use_case, _ = _make_create_alert()

    alert = use_case.run(
        user_id=UserId(uuid4()),
        name="Mid-range land",
        portal_slugs=frozenset({"idealista"}),
        frequency_seconds=900,
        condition_strings=["price:BETWEEN:50000,200000"],
    )

    [condition] = alert.conditions.children
    assert condition.value == (Decimal("50000"), Decimal("200000"))


def test_coerces_numeric_fields_to_int() -> None:
    use_case, _ = _make_create_alert()

    alert = use_case.run(
        user_id=UserId(uuid4()),
        name="At least 3 rooms",
        portal_slugs=frozenset({"idealista"}),
        frequency_seconds=900,
        condition_strings=["rooms:GTE:3"],
    )

    [condition] = alert.conditions.children
    assert condition.value == 3


def test_nullary_operator_takes_no_value() -> None:
    use_case, _ = _make_create_alert()

    alert = use_case.run(
        user_id=UserId(uuid4()),
        name="Has a garden",
        portal_slugs=frozenset({"idealista"}),
        frequency_seconds=900,
        condition_strings=["features.has_garden:EXISTS"],
    )

    [condition] = alert.conditions.children
    assert condition.operator is Operator.EXISTS
    assert condition.value is None


def test_multiple_conditions_are_combined_with_and() -> None:
    use_case, _ = _make_create_alert()

    alert = use_case.run(
        user_id=UserId(uuid4()),
        name="Land in Pontevedra under 20/m2",
        portal_slugs=frozenset({"idealista"}),
        frequency_seconds=900,
        condition_strings=["province:EQ:36", "price_per_m2:LTE:20"],
    )

    assert len(alert.conditions.children) == 2


def test_unknown_field_raises_invalid_condition_error() -> None:
    use_case, _ = _make_create_alert()

    with pytest.raises(InvalidConditionError):
        use_case.run(
            user_id=UserId(uuid4()),
            name="Bad field",
            portal_slugs=frozenset({"idealista"}),
            frequency_seconds=900,
            condition_strings=["not_a_real_field:EQ:1"],
        )


def test_operator_not_valid_for_field_type_raises() -> None:
    use_case, _ = _make_create_alert()

    with pytest.raises(InvalidConditionError):
        use_case.run(
            user_id=UserId(uuid4()),
            name="Bad operator",
            portal_slugs=frozenset({"idealista"}),
            frequency_seconds=900,
            condition_strings=["province:CONTAINS:36"],
        )


def test_malformed_condition_string_raises() -> None:
    use_case, _ = _make_create_alert()

    with pytest.raises(InvalidConditionError):
        use_case.run(
            user_id=UserId(uuid4()),
            name="No operator",
            portal_slugs=frozenset({"idealista"}),
            frequency_seconds=900,
            condition_strings=["province"],
        )
