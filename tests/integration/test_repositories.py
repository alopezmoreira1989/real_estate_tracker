"""Integration tests: domain <-> SQLite round-trips through the repositories."""

from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from real_estate.domain.model import (
    AlertCondition,
    AlertId,
    Area,
    Features,
    GroupOperator,
    Location,
    Media,
    Money,
    Operator,
    Property,
    PropertyId,
    RuleGroup,
    SearchAlert,
    UserId,
)
from real_estate.domain.vocabulary import (
    LandType,
    ListingStatus,
    ListingType,
    Municipality,
    PropertyType,
    Province,
)

NOW = datetime(2026, 7, 4, 12, 0)  # naive: SQLite does not persist tz


def _property() -> Property:
    return Property(
        id=PropertyId(uuid4()),
        listing_type=ListingType.SALE,
        property_type=PropertyType.LAND,
        land_type=LandType.URBANIZABLE,
        location=Location(
            province=Province.PONTEVEDRA,
            municipality=Municipality(ine_code="36038", name="Vigo"),
            district="Centro",
            postal_code="36201",
        ),
        title="Urbanizable plot near water",
        status=ListingStatus.ACTIVE,
        price=Money(Decimal("60000")),
        area=Area(Decimal("3000")),
        plot_area=Area(Decimal("5000")),
        features=Features(has_garden=True, has_lift=None),
        attributes={"energy_rating": "B"},
        media=Media(images=("https://cdn.example/1.jpg",)),
        description="A nice plot",
    )


def _alert(user_id: UserId) -> SearchAlert:
    # ALL( province == 36, price_per_m2 <= 20, NONE( description contains "occupied" ) )
    conditions = RuleGroup(
        GroupOperator.ALL,
        (
            AlertCondition("province", Operator.EQ, "36"),
            AlertCondition("price_per_m2", Operator.LTE, Decimal("20")),
            RuleGroup(
                GroupOperator.NONE,
                (AlertCondition("description", Operator.CONTAINS, "occupied"),),
            ),
        ),
    )
    return SearchAlert.create(
        id=AlertId(uuid4()),
        user_id=user_id,
        name="Urbanizable land in Pontevedra",
        portal_slugs=frozenset({"idealista", "fotocasa"}),
        frequency_seconds=900,
        conditions=conditions,
        now=NOW,
    )


def test_property_round_trips(persistence) -> None:
    prop = _property()
    with persistence.new_uow() as uow:
        uow.properties.add(prop)
        uow.commit()

    with persistence.new_uow() as uow:
        loaded = uow.properties.get(prop.id)

    assert loaded == prop
    assert loaded is not None
    assert loaded.price_per_m2 is not None
    assert loaded.price_per_m2.amount == Decimal("20")


def test_alert_round_trips_with_condition_tree(persistence) -> None:
    alert = _alert(persistence.user_id)
    with persistence.new_uow() as uow:
        uow.alerts.add(alert)
        uow.commit()

    with persistence.new_uow() as uow:
        loaded = uow.alerts.get(alert.id)

    assert loaded is not None
    assert loaded.name == alert.name
    assert loaded.portal_slugs == {"idealista", "fotocasa"}
    assert loaded.frequency_seconds == 900
    assert loaded.conditions == alert.conditions
    assert loaded.conditions.leaf_count() == 3


def test_alert_add_upserts_an_existing_alert_in_place(persistence) -> None:
    """Re-saving an already-persisted alert (e.g. RunAlertCycle calling
    mark_run() then uow.alerts.add(alert), Phase 5) must update in place —
    not raise a duplicate primary key error, and not duplicate/orphan its
    condition rows or portal subscriptions."""
    alert = _alert(persistence.user_id)
    with persistence.new_uow() as uow:
        uow.alerts.add(alert)
        uow.commit()

    alert.mark_run(now=NOW)
    with persistence.new_uow() as uow:
        uow.alerts.add(alert)  # re-save the mutated aggregate
        uow.commit()

    with persistence.new_uow() as uow:
        loaded = uow.alerts.get(alert.id)

    assert loaded is not None
    assert loaded.last_run_at == NOW
    assert loaded.portal_slugs == {"idealista", "fotocasa"}
    assert loaded.conditions == alert.conditions
    assert loaded.conditions.leaf_count() == 3


def test_list_for_user_returns_only_that_users_alerts(persistence) -> None:
    alert = _alert(persistence.user_id)
    with persistence.new_uow() as uow:
        uow.alerts.add(alert)
        uow.commit()

    with persistence.new_uow() as uow:
        mine = uow.alerts.list_for_user(alert.user_id)
        others = uow.alerts.list_for_user(UserId(uuid4()))

    assert [a.id for a in mine] == [alert.id]
    assert others == []


def test_rollback_discards_changes(persistence) -> None:
    prop = _property()
    with persistence.new_uow() as uow:
        uow.properties.add(prop)
        uow.rollback()

    with persistence.new_uow() as uow:
        assert uow.properties.get(prop.id) is None


def test_uncommitted_work_is_rolled_back_on_exit(persistence) -> None:
    alert = _alert(persistence.user_id)
    with persistence.new_uow() as uow:
        uow.alerts.add(alert)
        # no commit -> __exit__ rolls back

    with persistence.new_uow() as uow:
        assert uow.alerts.get(alert.id) is None
