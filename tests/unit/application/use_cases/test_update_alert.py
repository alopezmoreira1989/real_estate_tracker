from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from types import TracebackType
from uuid import uuid4

import pytest

from real_estate.application.use_cases.update_alert import AlertNotFoundError, UpdateAlert
from real_estate.domain.model.alert import SearchAlert
from real_estate.domain.model.conditions import AlertCondition, GroupOperator, Operator, RuleGroup
from real_estate.domain.model.identifiers import AlertId, UserId
from real_estate.domain.rules import default_registry

NOW = datetime(2026, 7, 10, 12, 0)
LATER = datetime(2026, 7, 10, 13, 0)


@dataclass
class _FixedClock:
    _now: datetime

    def now(self) -> datetime:
        return self._now


class _FakeAlertRepo:
    def __init__(self, seeded: SearchAlert | None = None) -> None:
        self._by_id = {seeded.id: seeded} if seeded is not None else {}

    def add(self, alert: SearchAlert) -> None:
        self._by_id[alert.id] = alert

    def get(self, alert_id: AlertId) -> SearchAlert | None:
        return self._by_id.get(alert_id)


class _FakeUoW:
    def __init__(self, alerts: _FakeAlertRepo) -> None:
        self.alerts = alerts
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


def _seeded_alert() -> SearchAlert:
    return SearchAlert.create(
        id=AlertId(uuid4()),
        user_id=UserId(uuid4()),
        name="Land in Pontevedra",
        portal_slugs=frozenset({"idealista"}),
        frequency_seconds=900,
        conditions=RuleGroup(GroupOperator.ALL, (AlertCondition("province", Operator.EQ, "36"),)),
        now=NOW,
    )


def _make_update_alert(alert: SearchAlert) -> tuple[UpdateAlert, _FakeUoW]:
    uow = _FakeUoW(_FakeAlertRepo(alert))
    use_case = UpdateAlert(
        uow_factory=lambda: uow, field_registry=default_registry(), clock=_FixedClock(LATER)
    )
    return use_case, uow


def test_renames_the_alert() -> None:
    alert = _seeded_alert()
    use_case, uow = _make_update_alert(alert)

    updated = use_case.run(alert_id=alert.id, name="Renamed alert")

    assert updated.name == "Renamed alert"
    assert updated.updated_at == LATER
    assert uow.committed is True


def test_changes_the_frequency() -> None:
    alert = _seeded_alert()
    use_case, _ = _make_update_alert(alert)

    updated = use_case.run(alert_id=alert.id, frequency_seconds=14400)

    assert updated.frequency_seconds == 14400


def test_deactivates_and_reactivates() -> None:
    alert = _seeded_alert()
    use_case, _ = _make_update_alert(alert)

    updated = use_case.run(alert_id=alert.id, is_active=False)
    assert updated.is_active is False

    reactivated = use_case.run(alert_id=alert.id, is_active=True)
    assert reactivated.is_active is True


def test_replaces_conditions() -> None:
    alert = _seeded_alert()
    use_case, _ = _make_update_alert(alert)

    updated = use_case.run(alert_id=alert.id, condition_strings=["price_per_m2:LTE:20"])

    [condition] = updated.conditions.children
    assert condition.field_key == "price_per_m2"


def test_leaves_unspecified_fields_untouched() -> None:
    alert = _seeded_alert()
    use_case, _ = _make_update_alert(alert)

    updated = use_case.run(alert_id=alert.id, name="Only the name changes")

    assert updated.frequency_seconds == 900
    assert updated.is_active is True
    assert updated.conditions == alert.conditions


def test_raises_for_an_unknown_alert() -> None:
    use_case, _ = _make_update_alert(_seeded_alert())

    with pytest.raises(AlertNotFoundError):
        use_case.run(alert_id=AlertId(uuid4()), name="Ghost")
