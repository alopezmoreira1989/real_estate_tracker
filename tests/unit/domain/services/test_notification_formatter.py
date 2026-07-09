from decimal import Decimal
from uuid import uuid4

from real_estate.domain.model.area import Area
from real_estate.domain.model.features import Features
from real_estate.domain.model.identifiers import PropertyId
from real_estate.domain.model.location import Location
from real_estate.domain.model.media import Media
from real_estate.domain.model.money import Money
from real_estate.domain.model.property import Property
from real_estate.domain.services.notification_formatter import format_match_message
from real_estate.domain.vocabulary import ListingStatus, ListingType, PropertyType, Province


def _property(*, price: Money | None, area: Area | None) -> Property:
    return Property(
        id=PropertyId(uuid4()),
        listing_type=ListingType.SALE,
        property_type=PropertyType.LAND,
        location=Location(province=Province.PONTEVEDRA),
        title="Urbanizable plot near water",
        status=ListingStatus.ACTIVE,
        price=price,
        area=area,
        features=Features(),
        media=Media(),
    )


def test_message_includes_title_price_area_and_link() -> None:
    prop = _property(price=Money(Decimal("60000")), area=Area(Decimal("3000")))

    message = format_match_message("Land in Pontevedra", prop, "https://idealista.com/1")

    assert message.title == "New match: Land in Pontevedra"
    assert prop.title in message.body
    assert "60,000 EUR" in message.body
    assert "3,000 m²" in message.body
    assert message.url == "https://idealista.com/1"


def test_message_omits_price_and_area_when_unknown() -> None:
    prop = _property(price=None, area=None)

    message = format_match_message("Land in Pontevedra", prop, None)

    assert message.body == prop.title
    assert message.url is None
