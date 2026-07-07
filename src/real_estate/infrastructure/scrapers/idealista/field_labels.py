"""Canonical value <-> Idealista URL segment / Spanish display label.

``PortalQuery.params`` carries canonical values (``"LAND"``, ``"SALE"``, an
INE province code) — the same scalars the Rule Engine and SearchPlanner use.
This module is the one place that knows how Idealista spells them in URLs and
on listing cards, so ``IdealistaScraper`` never invents portal knowledge
inline (docs/architecture/05-normalization.md, ADR-009 confinement principle
applied to scraping too).

Only the LAND + SALE + province-level search path has been verified against a
real saved page (``tests/fixtures/idealista/search_results_page.html`` —
"71 terrenos en Pontevedra"). The rest follow the same observed URL pattern
(``/{operation}-{type}/{province-slug}-{province-slug}/``) by inference and
should be spot-checked against the live site before being relied on.
"""

from __future__ import annotations

import re
import unicodedata

from real_estate.domain.vocabulary import Province

# operation -> (URL segment, Spanish label used to seed the raw "operacion" field)
_LISTING_TYPE = {
    "SALE": ("venta", "Venta"),
    "RENT": ("alquiler", "Alquiler"),
}

# property type -> (URL segment, Spanish label used to seed the raw "tipo" field)
# "terrenos"/"Suelo" is the verified pair; the others are Idealista's documented
# URL scheme applied by inference, not yet checked against a real page.
_PROPERTY_TYPE = {
    "LAND": ("terrenos", "Suelo"),
    "FLAT": ("viviendas", "Piso"),
    "PENTHOUSE": ("viviendas", "Ático"),
    "DUPLEX": ("viviendas", "Dúplex"),
    "STUDIO": ("viviendas", "Estudio"),
    "HOUSE": ("viviendas", "Casa"),
    "CHALET": ("viviendas", "Chalet"),
    "GARAGE": ("garajes", "Garaje"),
    "STORAGE_ROOM": ("trasteros", "Trastero"),
    "OFFICE": ("oficinas", "Oficina"),
    "COMMERCIAL": ("locales", "Local"),
    "BUILDING": ("edificios", "Edificio"),
}

_DEFAULT_LISTING_TYPE = ("venta", "Venta")
_DEFAULT_PROPERTY_TYPE = ("viviendas", "Piso")


def listing_type_url_segment(canonical: str | None) -> str:
    return _LISTING_TYPE.get(canonical or "", _DEFAULT_LISTING_TYPE)[0]


def listing_type_label(canonical: str | None) -> str:
    return _LISTING_TYPE.get(canonical or "", _DEFAULT_LISTING_TYPE)[1]


def property_type_url_segment(canonical: str | None) -> str:
    return _PROPERTY_TYPE.get(canonical or "", _DEFAULT_PROPERTY_TYPE)[0]


def property_type_label(canonical: str | None) -> str:
    return _PROPERTY_TYPE.get(canonical or "", _DEFAULT_PROPERTY_TYPE)[1]


def province_label(code: str | None) -> str:
    if not code:
        return ""
    province = Province.from_code(code)
    if province is Province.UNKNOWN:
        return ""
    return province.display_name.split("/")[0]


def province_url_slug(code: str | None) -> str:
    label = province_label(code)
    return _slugify(label)


def _slugify(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", "-", stripped.lower()).strip("-")
