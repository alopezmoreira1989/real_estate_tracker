from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from real_estate.application.ports import PortalCapabilities
from real_estate.application.services.search_planner import SearchPlanner
from real_estate.domain.model.alert import SearchAlert
from real_estate.domain.model.conditions import AlertCondition, GroupOperator, Operator, RuleGroup
from real_estate.domain.model.identifiers import AlertId, UserId

_NOW = datetime(2026, 7, 6, tzinfo=UTC)

_IDEALISTA_CAPABILITIES = PortalCapabilities(
    portal_slug="idealista",
    pushable_fields=frozenset({"province", "property_type", "listing_type", "price"}),
    rate_limit_per_second=1.0,
    circuit_breaker_failure_threshold=5,
    circuit_breaker_cooldown_seconds=60.0,
)


def _alert(
    *, conditions: RuleGroup, portal_slugs: frozenset[str] = frozenset({"idealista"})
) -> SearchAlert:
    return SearchAlert.create(
        id=AlertId(uuid4()),
        user_id=UserId(uuid4()),
        name="test alert",
        portal_slugs=portal_slugs,
        frequency_seconds=300,
        conditions=conditions,
        now=_NOW,
    )


def _land_pontevedra_conditions(*extra: AlertCondition) -> RuleGroup:
    return RuleGroup(
        GroupOperator.ALL,
        (
            AlertCondition("province", Operator.EQ, "36"),
            AlertCondition("property_type", Operator.EQ, "LAND"),
            AlertCondition("listing_type", Operator.EQ, "SALE"),
            *extra,
        ),
    )


def test_ten_alerts_on_the_same_search_yield_one_planned_query() -> None:
    alerts = [
        _alert(
            conditions=_land_pontevedra_conditions(
                AlertCondition("description", Operator.CONTAINS, f"keyword-{i}")
            )
        )
        for i in range(10)
    ]
    planner = SearchPlanner({"idealista": _IDEALISTA_CAPABILITIES})

    planned = planner.plan(alerts)

    assert len(planned) == 1
    assert len(planned[0].alerts) == 10


def test_signature_is_identical_regardless_of_condition_order_or_user() -> None:
    alert_a = _alert(
        conditions=RuleGroup(
            GroupOperator.ALL,
            (
                AlertCondition("province", Operator.EQ, "36"),
                AlertCondition("property_type", Operator.EQ, "LAND"),
            ),
        )
    )
    alert_b = _alert(
        conditions=RuleGroup(
            GroupOperator.ALL,
            (
                AlertCondition("property_type", Operator.EQ, "LAND"),
                AlertCondition("province", Operator.EQ, "36"),
            ),
        )
    )
    planner = SearchPlanner({"idealista": _IDEALISTA_CAPABILITIES})

    planned = planner.plan([alert_a, alert_b])

    assert len(planned) == 1


def test_different_pushable_conditions_yield_different_signatures() -> None:
    alert_pontevedra = _alert(conditions=_land_pontevedra_conditions())
    alert_lugo = _alert(
        conditions=RuleGroup(
            GroupOperator.ALL,
            (
                AlertCondition("province", Operator.EQ, "27"),
                AlertCondition("property_type", Operator.EQ, "LAND"),
                AlertCondition("listing_type", Operator.EQ, "SALE"),
            ),
        )
    )
    planner = SearchPlanner({"idealista": _IDEALISTA_CAPABILITIES})

    planned = planner.plan([alert_pontevedra, alert_lugo])

    assert len(planned) == 2
    assert planned[0].signature != planned[1].signature


def test_price_between_maps_to_min_and_max_params() -> None:
    alert = _alert(
        conditions=RuleGroup(
            GroupOperator.ALL,
            (
                AlertCondition("province", Operator.EQ, "36"),
                AlertCondition("price", Operator.BETWEEN, (Decimal("50000"), Decimal("200000"))),
            ),
        )
    )
    planner = SearchPlanner({"idealista": _IDEALISTA_CAPABILITIES})

    [planned] = planner.plan([alert])

    assert planned.query.params["price_min"] == "50000"
    assert planned.query.params["price_max"] == "200000"


def test_non_pushable_conditions_are_left_out_of_the_query() -> None:
    alert = _alert(
        conditions=RuleGroup(
            GroupOperator.ALL,
            (
                AlertCondition("province", Operator.EQ, "36"),
                AlertCondition("description", Operator.CONTAINS, "water"),
                AlertCondition("rooms", Operator.GTE, 3),
            ),
        )
    )
    planner = SearchPlanner({"idealista": _IDEALISTA_CAPABILITIES})

    [planned] = planner.plan([alert])

    assert planned.query.params == {"province": "36"}


def test_top_level_or_group_is_not_decomposed_and_fetches_broad() -> None:
    alert = _alert(
        conditions=RuleGroup(
            GroupOperator.ANY,
            (
                AlertCondition("province", Operator.EQ, "36"),
                AlertCondition("province", Operator.EQ, "27"),
            ),
        )
    )
    planner = SearchPlanner({"idealista": _IDEALISTA_CAPABILITIES})

    [planned] = planner.plan([alert])

    assert planned.query.params == {}


def test_unknown_portal_produces_an_empty_query_rather_than_raising() -> None:
    alert = _alert(conditions=_land_pontevedra_conditions(), portal_slugs=frozenset({"fotocasa"}))
    planner = SearchPlanner({"idealista": _IDEALISTA_CAPABILITIES})

    [planned] = planner.plan([alert])

    assert planned.portal_slug == "fotocasa"
    assert planned.query.params == {}
