from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from real_estate.domain.model import (
    AlertCondition,
    AlertId,
    AlertMatch,
    Area,
    GroupOperator,
    Location,
    Money,
    Operator,
    Property,
    PropertyId,
    RuleGroup,
    SearchAlert,
    UserId,
)
from real_estate.domain.rules import SpecificationFactory, default_registry
from real_estate.domain.services import AlertEngine
from real_estate.domain.vocabulary import ListingType, PropertyType, Province

NOW = datetime(2026, 7, 5, 12, 0, tzinfo=UTC)


def _engine() -> AlertEngine:
    return AlertEngine(SpecificationFactory(default_registry()))


def _alert() -> SearchAlert:
    conditions = RuleGroup(
        GroupOperator.ALL,
        (
            AlertCondition("province", Operator.EQ, "36"),
            AlertCondition("price_per_m2", Operator.LTE, Decimal("20")),
        ),
    )
    return SearchAlert.create(
        id=AlertId(uuid4()),
        user_id=UserId(uuid4()),
        name="cheap land in Pontevedra",
        portal_slugs=frozenset({"idealista"}),
        frequency_seconds=900,
        conditions=conditions,
        now=NOW,
    )


def _prop(province: Province, ppm2: Decimal) -> Property:
    # price/area chosen so price_per_m2 == ppm2
    return Property(
        id=PropertyId(uuid4()),
        listing_type=ListingType.SALE,
        property_type=PropertyType.LAND,
        location=Location(province=province),
        title="Plot",
        price=Money(ppm2 * Decimal("1000")),
        area=Area(Decimal("1000")),
    )


def test_engine_returns_only_matching_properties() -> None:
    alert = _alert()
    match_me = _prop(Province.PONTEVEDRA, Decimal("15"))
    too_expensive = _prop(Province.PONTEVEDRA, Decimal("30"))
    wrong_province = _prop(Province.MADRID, Decimal("10"))

    matches = _engine().evaluate(alert, [match_me, too_expensive, wrong_province], now=NOW)

    assert [m.property_id for m in matches] == [match_me.id]
    assert matches[0].alert_id == alert.id
    assert matches[0].matched_at == NOW


def test_matches_dedupe_by_natural_key() -> None:
    alert = _alert()
    prop = _prop(Province.PONTEVEDRA, Decimal("15"))
    a = AlertMatch(alert.id, prop.id, matched_at=NOW)
    b = AlertMatch(alert.id, prop.id, matched_at=datetime(2026, 1, 1, tzinfo=UTC))
    assert a == b
    assert len({a, b}) == 1


def test_no_candidates_no_matches() -> None:
    assert _engine().evaluate(_alert(), [], now=NOW) == []
