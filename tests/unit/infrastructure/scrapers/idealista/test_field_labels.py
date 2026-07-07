from real_estate.infrastructure.scrapers.idealista import field_labels


def test_listing_type_verified_pair() -> None:
    assert field_labels.listing_type_url_segment("SALE") == "venta"
    assert field_labels.listing_type_label("SALE") == "Venta"


def test_listing_type_rent() -> None:
    assert field_labels.listing_type_url_segment("RENT") == "alquiler"
    assert field_labels.listing_type_label("RENT") == "Alquiler"


def test_listing_type_falls_back_to_sale_for_unknown_or_missing() -> None:
    assert field_labels.listing_type_url_segment(None) == "venta"
    assert field_labels.listing_type_url_segment("AUCTION") == "venta"


def test_property_type_verified_pair() -> None:
    assert field_labels.property_type_url_segment("LAND") == "terrenos"
    assert field_labels.property_type_label("LAND") == "Suelo"


def test_property_type_falls_back_to_flat_for_unknown_or_missing() -> None:
    assert field_labels.property_type_url_segment(None) == "viviendas"
    assert field_labels.property_type_label(None) == "Piso"


def test_province_label_and_slug_for_a_single_word_province() -> None:
    assert field_labels.province_label("36") == "Pontevedra"
    assert field_labels.province_url_slug("36") == "pontevedra"


def test_province_label_and_slug_for_a_bilingual_province_uses_first_part() -> None:
    # Alicante/Alacant -> INE 03
    assert field_labels.province_label("03") == "Alicante"
    assert field_labels.province_url_slug("03") == "alicante"


def test_province_label_and_slug_empty_for_missing_or_unknown_code() -> None:
    assert field_labels.province_label(None) == ""
    assert field_labels.province_url_slug(None) == ""
    assert field_labels.province_label("99") == ""
