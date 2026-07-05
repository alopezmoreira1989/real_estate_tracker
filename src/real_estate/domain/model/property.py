"""The canonical Property entity."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from real_estate.domain.model.area import Area, PricePerM2
from real_estate.domain.model.features import Features
from real_estate.domain.model.identifiers import PropertyId
from real_estate.domain.model.location import Location
from real_estate.domain.model.media import Media
from real_estate.domain.model.money import Money
from real_estate.domain.vocabulary import LandType, ListingStatus, ListingType, PropertyType


@dataclass(frozen=True, slots=True)
class Property:
    """A portal-independent, normalized listing — the only shape the Rule
    Engine ever evaluates (docs/architecture/02-domain-model.md §2).

    Immutable snapshot: a re-scrape produces a new snapshot rather than mutating
    in place. ``price_per_m2`` is derived from the price and area so its units
    are always consistent.
    """

    id: PropertyId
    listing_type: ListingType
    property_type: PropertyType
    location: Location
    title: str
    status: ListingStatus = ListingStatus.UNKNOWN
    land_type: LandType | None = None
    price: Money | None = None
    area: Area | None = None
    plot_area: Area | None = None
    rooms: int | None = None
    bathrooms: int | None = None
    features: Features = field(default_factory=Features)
    attributes: dict[str, str] = field(default_factory=dict)
    description: str = ""
    media: Media = field(default_factory=Media)
    published_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.land_type is not None and self.property_type is not PropertyType.LAND:
            raise ValueError("land_type is only valid when property_type is LAND")
        if self.rooms is not None and self.rooms < 0:
            raise ValueError("rooms must not be negative")
        if self.bathrooms is not None and self.bathrooms < 0:
            raise ValueError("bathrooms must not be negative")

    @property
    def price_per_m2(self) -> PricePerM2 | None:
        """Price per built m², or ``None`` when price or area is unknown."""
        if self.price is None or self.area is None:
            return None
        return PricePerM2.from_price_and_area(self.price, self.area)
