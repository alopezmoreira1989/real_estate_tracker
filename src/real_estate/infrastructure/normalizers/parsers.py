"""Shared Spanish-locale value parsers.

Portals write numbers using Spanish conventions: ``.`` as the thousands
separator and ``,`` as the decimal separator, often with a currency symbol or
unit suffix attached (``"120.000 €"``, ``"3.000 m²"``, ``"1.234,56"``). These
parsers centralize that logic (docs/architecture/05-normalization.md §2) so it
is written, and tested, exactly once.

Never uses ``float(str)`` — values are parsed straight into :class:`Decimal`.
Unparseable or missing input returns ``None`` rather than raising; a bad field
must never crash normalization of the rest of the listing (CLAUDE.md §12).
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from real_estate.domain.model.area import Area
from real_estate.domain.model.money import Money
from real_estate.domain.vocabulary import Currency

_STRIP = ("€", "$", "m²", "m2")
_NUMERIC = re.compile(r"-?[\d.,]+")
_DIGITS = re.compile(r"\d+")


def _clean(text: str) -> str:
    cleaned = text
    for token in _STRIP:
        cleaned = cleaned.replace(token, "")
    return cleaned.strip()


def _parse_decimal(text: str | None) -> Decimal | None:
    if text is None:
        return None
    match = _NUMERIC.search(_clean(text))
    if match is None:
        return None
    token = match.group()
    # Spanish locale: "." is a thousands separator, "," is the decimal point.
    token = token.replace(".", "").replace(",", ".") if "," in token else token.replace(".", "")
    try:
        return Decimal(token)
    except InvalidOperation:
        return None


def parse_money(text: str | None, currency: Currency = Currency.EUR) -> Money | None:
    """Parse a Spanish-locale money string, e.g. ``"120.000 €"`` -> 120000 EUR."""
    amount = _parse_decimal(text)
    if amount is None:
        return None
    try:
        return Money(amount, currency)
    except (TypeError, ValueError):
        return None


def parse_area(text: str | None) -> Area | None:
    """Parse a Spanish-locale area string, e.g. ``"3.000 m²"`` -> 3000 m²."""
    value = _parse_decimal(text)
    if value is None:
        return None
    try:
        return Area(value)
    except (TypeError, ValueError):
        return None


def parse_int(text: str | None) -> int | None:
    """Parse the first integer found in ``text``, e.g. ``"3 habitaciones"`` -> 3."""
    if text is None:
        return None
    match = _DIGITS.search(_clean(text))
    if match is None:
        return None
    return int(match.group())
