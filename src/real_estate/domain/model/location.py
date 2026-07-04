"""Geographic value objects: a point and a full location."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal

from real_estate.domain.vocabulary import Municipality, Province

_POSTAL_CODE = re.compile(r"^\d{5}$")


@dataclass(frozen=True, slots=True)
class GeoPoint:
    """A WGS84 coordinate."""

    latitude: Decimal
    longitude: Decimal

    def __post_init__(self) -> None:
        if not (Decimal(-90) <= self.latitude <= Decimal(90)):
            raise ValueError("latitude must be within [-90, 90]")
        if not (Decimal(-180) <= self.longitude <= Decimal(180)):
            raise ValueError("longitude must be within [-180, 180]")


@dataclass(frozen=True, slots=True)
class Location:
    """Where a property is, using controlled geography.

    ``province`` is always present (falling back to ``Province.UNKNOWN`` when a
    portal did not disclose it). When a ``municipality`` is given it must belong
    to ``province`` — validated so inconsistent data cannot be constructed.
    """

    province: Province
    country: str = "ES"
    municipality: Municipality | None = None
    district: str | None = None
    postal_code: str | None = None
    geo: GeoPoint | None = None

    def __post_init__(self) -> None:
        if self.municipality is not None and self.municipality.province is not self.province:
            raise ValueError(
                f"Municipality {self.municipality.name} belongs to "
                f"{self.municipality.province.display_name}, not {self.province.display_name}"
            )
        if self.postal_code is not None and not _POSTAL_CODE.match(self.postal_code):
            raise ValueError(f"postal_code must be 5 digits, got {self.postal_code!r}")
