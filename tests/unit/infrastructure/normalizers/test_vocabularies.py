import pytest

from real_estate.domain.vocabulary import LandType, PropertyType, Province
from real_estate.infrastructure.normalizers.vocabularies import (
    resolve_land_type,
    resolve_property_type,
    resolve_province,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("piso", PropertyType.FLAT),
        ("Ático", PropertyType.PENTHOUSE),
        ("chalet", PropertyType.CHALET),
        ("Suelo", PropertyType.LAND),
        ("Terreno", PropertyType.LAND),
        ("Garaje", PropertyType.GARAGE),
    ],
)
def test_known_property_type_terms_resolve(text: str, expected: PropertyType) -> None:
    assert resolve_property_type(text) is expected


def test_unknown_property_type_falls_back_to_other() -> None:
    assert resolve_property_type("something unmapped") is PropertyType.OTHER
    assert resolve_property_type(None) is PropertyType.OTHER


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Urbano", LandType.URBAN),
        ("Suelo urbanizable", LandType.URBANIZABLE),
        ("Rústico", LandType.RUSTIC),
        ("No urbanizable", LandType.NON_DEVELOPABLE),
    ],
)
def test_known_land_type_terms_resolve(text: str, expected: LandType) -> None:
    assert resolve_land_type(text) is expected


def test_unknown_land_type_falls_back_to_unknown() -> None:
    assert resolve_land_type("something unmapped") is LandType.UNKNOWN
    assert resolve_land_type(None) is LandType.UNKNOWN


def test_every_province_resolves_from_its_own_display_name() -> None:
    for province in Province:
        if province is Province.UNKNOWN:
            continue
        for part in province.display_name.split("/"):
            assert resolve_province(part) is province


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("La Coruña", Province.A_CORUNA),
        ("Coruña", Province.A_CORUNA),
        ("Vizcaya", Province.BIZKAIA),
        ("Guipúzcoa", Province.GIPUZKOA),
        ("Gerona", Province.GIRONA),
        ("Lérida", Province.LLEIDA),
        ("Islas Baleares", Province.ILLES_BALEARS),
    ],
)
def test_known_province_aliases_resolve(text: str, expected: Province) -> None:
    assert resolve_province(text) is expected


def test_unknown_province_falls_back_to_unknown() -> None:
    assert resolve_province("Nowhereland") is Province.UNKNOWN
    assert resolve_province(None) is Province.UNKNOWN
