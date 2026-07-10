from datetime import UTC, datetime
from uuid import uuid4

import pytest

from real_estate.domain.errors import InvalidAlertError
from real_estate.domain.model import (
    AlertCondition,
    AlertId,
    GroupOperator,
    Operator,
    RuleGroup,
    SearchAlert,
    UserId,
)

NOW = datetime(2026, 7, 4, 12, 0, tzinfo=UTC)


def _conditions() -> RuleGroup:
    return RuleGroup(GroupOperator.ALL, (AlertCondition("province", Operator.EQ, "36"),))


def _create(**overrides: object) -> SearchAlert:
    base: dict[str, object] = dict(
        id=AlertId(uuid4()),
        user_id=UserId(uuid4()),
        name="Urbanizable land in Pontevedra",
        portal_slugs=frozenset({"idealista"}),
        frequency_seconds=900,
        conditions=_conditions(),
        now=NOW,
    )
    base.update(overrides)
    return SearchAlert.create(**base)  # type: ignore[arg-type]


def test_create_sets_timestamps_and_is_active() -> None:
    alert = _create()
    assert alert.created_at == NOW
    assert alert.updated_at == NOW
    assert alert.is_active is True


def test_create_rejects_empty_name() -> None:
    with pytest.raises(InvalidAlertError):
        _create(name="  ")


def test_create_rejects_no_portals() -> None:
    with pytest.raises(InvalidAlertError):
        _create(portal_slugs=frozenset())


def test_create_rejects_too_frequent() -> None:
    with pytest.raises(InvalidAlertError):
        _create(frequency_seconds=30)


def test_replace_conditions_bumps_updated_at() -> None:
    alert = _create()
    later = datetime(2026, 7, 5, tzinfo=UTC)
    new = RuleGroup(GroupOperator.ALL, (AlertCondition("rooms", Operator.GTE, 3),))
    alert.replace_conditions(new, now=later)
    assert alert.conditions is new
    assert alert.updated_at == later


def test_deactivate_and_mark_run() -> None:
    alert = _create()
    later = datetime(2026, 7, 5, tzinfo=UTC)
    alert.deactivate(now=later)
    assert alert.is_active is False
    alert.mark_run(now=later)
    assert alert.last_run_at == later


def test_set_frequency_updates_it_and_bumps_updated_at() -> None:
    alert = _create()
    later = datetime(2026, 7, 5, tzinfo=UTC)
    alert.set_frequency(14400, now=later)
    assert alert.frequency_seconds == 14400
    assert alert.updated_at == later


def test_set_frequency_rejects_too_frequent() -> None:
    alert = _create()
    with pytest.raises(InvalidAlertError):
        alert.set_frequency(30, now=NOW)
