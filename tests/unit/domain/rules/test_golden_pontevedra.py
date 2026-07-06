"""Golden fixture: the flagship 'Urbanizable land in Pontevedra' alert.

ALL(
  province == 36,
  property_type == LAND,
  land_type == URBANIZABLE,
  price_per_m2 <= 20,
  area >= 3000,
  description contains "water",
  NONE( description contains "occupied" ),
)
"""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from real_estate.domain.model import (
    AlertCondition,
    AlertId,
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
from real_estate.domain.vocabulary import LandType, ListingType, PropertyType, Province

NOW = datetime(2026, 7, 5, tzinfo=UTC)


def _golden_alert() -> SearchAlert:
    conditions = RuleGroup(
        GroupOperator.ALL,
        (
            AlertCondition("province", Operator.EQ, "36"),
            AlertCondition("property_type", Operator.EQ, "LAND"),
            AlertCondition("land_type", Operator.EQ, "URBANIZABLE"),
            AlertCondition("price_per_m2", Operator.LTE, Decimal("20")),
            AlertCondition("area", Operator.GTE, Decimal("3000")),
            AlertCondition("description", Operator.CONTAINS, "water"),
            RuleGroup(
                GroupOperator.NONE,
                (AlertCondition("description", Operator.CONTAINS, "occupied"),),
            ),
        ),
    )
    return SearchAlert.create(
        id=AlertId(uuid4()),
        user_id=UserId(uuid4()),
        name="Urbanizable land in Pontevedra",
        portal_slugs=frozenset({"idealista"}),
        frequency_seconds=900,
        conditions=conditions,
        now=NOW,
    )


def _land(
    *,
    province: Province = Province.PONTEVEDRA,
    land_type: LandType = LandType.URBANIZABLE,
    price: str = "60000",
    area: str = "3000",
    description: str = "Great urbanizable plot with water supply",
) -> Property:
    return Property(
        id=PropertyId(uuid4()),
        listing_type=ListingType.SALE,
        property_type=PropertyType.LAND,
        land_type=land_type,
        location=Location(province=province),
        title="Plot",
        price=Money(Decimal(price)),
        area=Area(Decimal(area)),
        description=description,
    )


def test_golden_alert_matches_only_the_qualifying_plot() -> None:
    engine = AlertEngine(SpecificationFactory(default_registry()))
    perfect = _land()  # ppm2 = 60000/3000 = 20, area 3000, has water, no occupied
    candidates = [
        perfect,
        _land(province=Province.MADRID),  # wrong province
        _land(land_type=LandType.RUSTIC),  # not urbanizable
        _land(price="90000"),  # ppm2 = 30 > 20
        _land(area="2000", price="40000"),  # area < 3000
        _land(description="urbanizable plot, no utilities"),  # no "water"
        _land(description="urbanizable plot with water but occupied"),  # excluded
    ]

    matches = engine.evaluate(_golden_alert(), candidates, now=NOW)

    assert [m.property_id for m in matches] == [perfect.id]
