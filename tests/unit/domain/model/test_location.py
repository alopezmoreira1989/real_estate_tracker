from decimal import Decimal

import pytest

from real_estate.domain.model import GeoPoint, Location
from real_estate.domain.vocabulary import Municipality, Province


def test_geopoint_rejects_out_of_range() -> None:
    with pytest.raises(ValueError):
        GeoPoint(latitude=Decimal("100"), longitude=Decimal("0"))
    with pytest.raises(ValueError):
        GeoPoint(latitude=Decimal("0"), longitude=Decimal("200"))


def test_location_defaults_country_to_es() -> None:
    loc = Location(province=Province.PONTEVEDRA)
    assert loc.country == "ES"


def test_location_accepts_matching_municipality() -> None:
    vigo = Municipality(ine_code="36038", name="Vigo")
    loc = Location(province=Province.PONTEVEDRA, municipality=vigo)
    assert loc.municipality is vigo


def test_location_rejects_municipality_from_other_province() -> None:
    madrid_city = Municipality(ine_code="28079", name="Madrid")
    with pytest.raises(ValueError):
        Location(province=Province.PONTEVEDRA, municipality=madrid_city)


def test_location_validates_postal_code() -> None:
    with pytest.raises(ValueError):
        Location(province=Province.MADRID, postal_code="123")
    assert Location(province=Province.MADRID, postal_code="28001").postal_code == "28001"
