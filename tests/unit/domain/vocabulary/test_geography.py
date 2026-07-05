import pytest

from real_estate.domain.vocabulary import Municipality, Province


def test_all_52_provinces_plus_unknown_are_present() -> None:
    # 52 real provinces + the UNKNOWN fallback.
    assert len(Province) == 53
    assert Province.UNKNOWN.code == "00"


def test_province_codes_are_unique_two_digit_strings() -> None:
    codes = [p.code for p in Province]
    assert len(codes) == len(set(codes))
    assert all(len(c) == 2 and c.isdigit() for c in codes)


def test_pontevedra_has_ine_code_36() -> None:
    assert Province.PONTEVEDRA.code == "36"
    assert Province.PONTEVEDRA.display_name == "Pontevedra"


def test_from_code_resolves_known_and_falls_back_to_unknown() -> None:
    assert Province.from_code("36") is Province.PONTEVEDRA
    assert Province.from_code("99") is Province.UNKNOWN


def test_municipality_derives_its_province_from_the_code_prefix() -> None:
    # 36038 = Vigo (province 36 = Pontevedra)
    vigo = Municipality(ine_code="36038", name="Vigo")
    assert vigo.province is Province.PONTEVEDRA


@pytest.mark.parametrize("bad_code", ["3603", "360388", "3603X", "abcde"])
def test_municipality_rejects_malformed_codes(bad_code: str) -> None:
    with pytest.raises(ValueError):
        Municipality(ine_code=bad_code, name="Somewhere")


def test_municipality_rejects_invalid_province_prefix() -> None:
    with pytest.raises(ValueError):
        Municipality(ine_code="99001", name="Nowhere")


def test_municipality_rejects_empty_name() -> None:
    with pytest.raises(ValueError):
        Municipality(ine_code="36038", name="   ")
