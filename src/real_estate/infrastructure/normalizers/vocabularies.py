"""Shared vocabulary dictionaries: portal free text -> controlled enum.

Shared across portals (docs/architecture/05-normalization.md §3) since the
underlying Spanish terms are largely portal-independent ("piso", "chalet",
"suelo urbanizable", province names). A portal whose own labels don't fit
these dictionaries can extend/override them in its own package.

Every ``resolve_*`` function is total: it never raises and always returns a
member of its enum, falling back to the documented ``OTHER``/``UNKNOWN``
member when the input is missing or unrecognized (CLAUDE.md §12 — normalizing
never drops a listing for an unmapped value). Callers are responsible for
recording a :class:`~real_estate.domain.ports.normalizer.NormalizationIssue`
when a fallback was used; see ``infrastructure/normalizers/base.py``.
"""

from __future__ import annotations

import unicodedata

from real_estate.domain.vocabulary import LandType, ListingType, PropertyType, Province


def _normalize_text(text: str) -> str:
    """Case- and accent-insensitive fold, mirroring the Rule Engine's own
    ``CONTAINS`` folding (``domain/rules/operators.py``). Duplicated
    intentionally: that helper is private to the domain layer, and vocabulary
    lookup here is an unrelated infrastructure concern, even though the
    underlying technique (NFKD strip + casefold) is identical.
    """
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return stripped.casefold().strip()


PROPERTY_TYPE_VOCAB: dict[str, PropertyType] = {
    "piso": PropertyType.FLAT,
    "apartamento": PropertyType.FLAT,
    "atico": PropertyType.PENTHOUSE,
    "duplex": PropertyType.DUPLEX,
    "estudio": PropertyType.STUDIO,
    "casa": PropertyType.HOUSE,
    "casa unifamiliar": PropertyType.HOUSE,
    "chalet": PropertyType.CHALET,
    "chalet adosado": PropertyType.CHALET,
    "adosado": PropertyType.CHALET,
    "suelo": PropertyType.LAND,
    "terreno": PropertyType.LAND,
    "finca rustica": PropertyType.LAND,
    "garaje": PropertyType.GARAGE,
    "plaza de garaje": PropertyType.GARAGE,
    "trastero": PropertyType.STORAGE_ROOM,
    "oficina": PropertyType.OFFICE,
    "local comercial": PropertyType.COMMERCIAL,
    "local": PropertyType.COMMERCIAL,
    "edificio": PropertyType.BUILDING,
}

LISTING_TYPE_VOCAB: dict[str, ListingType] = {
    "venta": ListingType.SALE,
    "compra": ListingType.SALE,
    "alquiler": ListingType.RENT,
    "arrendamiento": ListingType.RENT,
    "subasta": ListingType.AUCTION,
    "traspaso": ListingType.TRANSFER,
}

LAND_TYPE_VOCAB: dict[str, LandType] = {
    "urbano": LandType.URBAN,
    "suelo urbano": LandType.URBAN,
    "urbanizable": LandType.URBANIZABLE,
    "suelo urbanizable": LandType.URBANIZABLE,
    "rustico": LandType.RUSTIC,
    "rustica": LandType.RUSTIC,
    "suelo rustico": LandType.RUSTIC,
    "no urbanizable": LandType.NON_DEVELOPABLE,
    "suelo no urbanizable": LandType.NON_DEVELOPABLE,
    "protegido": LandType.NON_DEVELOPABLE,
}

# Common alternate/older Spanish names for bilingually-named provinces that
# aren't already covered by splitting Province.display_name on "/"
# (e.g. "Alicante/Alacant" already yields both "alicante" and "alacant").
_PROVINCE_ALIASES: dict[str, Province] = {
    "coruna": Province.A_CORUNA,
    "la coruna": Province.A_CORUNA,
    "baleares": Province.ILLES_BALEARS,
    "islas baleares": Province.ILLES_BALEARS,
    "guipuzcoa": Province.GIPUZKOA,
    "vizcaya": Province.BIZKAIA,
    "gerona": Province.GIRONA,
    "lerida": Province.LLEIDA,
    "rioja": Province.LA_RIOJA,
}


def _build_province_vocab() -> dict[str, Province]:
    vocab: dict[str, Province] = {}
    for province in Province:
        if province is Province.UNKNOWN:
            continue
        for part in province.display_name.split("/"):
            vocab[_normalize_text(part)] = province
    vocab.update(_PROVINCE_ALIASES)
    return vocab


PROVINCE_VOCAB: dict[str, Province] = _build_province_vocab()


def resolve_property_type(text: str | None) -> PropertyType:
    """Map portal free text to a canonical :class:`PropertyType`, or ``OTHER``."""
    if text is None:
        return PropertyType.OTHER
    return PROPERTY_TYPE_VOCAB.get(_normalize_text(text), PropertyType.OTHER)


def resolve_land_type(text: str | None) -> LandType:
    """Map portal free text to a canonical :class:`LandType`, or ``UNKNOWN``."""
    if text is None:
        return LandType.UNKNOWN
    return LAND_TYPE_VOCAB.get(_normalize_text(text), LandType.UNKNOWN)


def resolve_listing_type(text: str | None) -> ListingType:
    """Map portal free text to a canonical :class:`ListingType`, or ``OTHER``."""
    if text is None:
        return ListingType.OTHER
    return LISTING_TYPE_VOCAB.get(_normalize_text(text), ListingType.OTHER)


def resolve_province(text: str | None) -> Province:
    """Map a portal province name to a canonical :class:`Province`, or ``UNKNOWN``."""
    if text is None:
        return Province.UNKNOWN
    return PROVINCE_VOCAB.get(_normalize_text(text), Province.UNKNOWN)
