"""SQLAlchemy adapter for :class:`PropertyRepository`.

Flattens the canonical :class:`Property` (with its value objects) onto the
``properties`` table and reconstitutes it on read.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from real_estate.domain.model.area import Area
from real_estate.domain.model.features import Features
from real_estate.domain.model.identifiers import PropertyId
from real_estate.domain.model.location import GeoPoint, Location
from real_estate.domain.model.media import Media
from real_estate.domain.model.money import Money
from real_estate.domain.model.property import Property
from real_estate.domain.vocabulary import (
    Currency,
    LandType,
    ListingStatus,
    ListingType,
    Municipality,
    PropertyType,
    Province,
)
from real_estate.infrastructure.persistence.models.orm import PriceHistoryModel, PropertyModel


def _to_model(prop: Property, *, now: datetime) -> PropertyModel:
    loc = prop.location
    ppm2 = prop.price_per_m2
    return PropertyModel(
        id=prop.id,
        listing_type=prop.listing_type.value,
        property_type=prop.property_type.value,
        land_type=prop.land_type.value if prop.land_type else None,
        province_ine=loc.province.code,
        municipality_ine=loc.municipality.ine_code if loc.municipality else None,
        municipality_name=loc.municipality.name if loc.municipality else None,
        district=loc.district,
        postal_code=loc.postal_code,
        lat=loc.geo.latitude if loc.geo else None,
        lng=loc.geo.longitude if loc.geo else None,
        price_amount=prop.price.amount if prop.price else None,
        price_currency=prop.price.currency.value if prop.price else None,
        area_m2=prop.area.square_meters if prop.area else None,
        plot_area_m2=prop.plot_area.square_meters if prop.plot_area else None,
        price_per_m2=ppm2.amount if ppm2 else None,
        rooms=prop.rooms,
        bathrooms=prop.bathrooms,
        features=asdict(prop.features),
        attributes=dict(prop.attributes),
        media={"images": list(prop.media.images), "videos": list(prop.media.videos)},
        title=prop.title,
        description=prop.description,
        status=prop.status.value,
        published_at=prop.published_at,
        first_seen_at=now,
        last_seen_at=now,
    )


def _to_domain(model: PropertyModel) -> Property:
    municipality = (
        Municipality(ine_code=model.municipality_ine, name=model.municipality_name)
        if model.municipality_ine and model.municipality_name
        else None
    )
    geo = (
        GeoPoint(latitude=model.lat, longitude=model.lng)
        if model.lat is not None and model.lng is not None
        else None
    )
    location = Location(
        province=Province.from_code(model.province_ine),
        municipality=municipality,
        district=model.district,
        postal_code=model.postal_code,
        geo=geo,
    )
    price = (
        Money(model.price_amount, Currency(model.price_currency))
        if model.price_amount is not None and model.price_currency
        else None
    )
    return Property(
        id=PropertyId(model.id),
        listing_type=ListingType(model.listing_type),
        property_type=PropertyType(model.property_type),
        location=location,
        title=model.title,
        status=ListingStatus(model.status),
        land_type=LandType(model.land_type) if model.land_type else None,
        price=price,
        area=Area(model.area_m2) if model.area_m2 is not None else None,
        plot_area=Area(model.plot_area_m2) if model.plot_area_m2 is not None else None,
        rooms=model.rooms,
        bathrooms=model.bathrooms,
        features=Features(**model.features),
        attributes=dict(model.attributes),
        media=Media(
            images=tuple(model.media.get("images", [])),
            videos=tuple(model.media.get("videos", [])),
        ),
        description=model.description,
        published_at=model.published_at,
    )


class SqlAlchemyPropertyRepository:
    """Persists canonical properties via a SQLAlchemy session."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, prop: Property) -> None:
        """Upsert ``prop``; appends a PriceHistory row only if the price changed.

        ``first_seen_at`` is preserved across re-scrapes (only ``last_seen_at``
        moves forward) — it marks when we first observed this property, which
        is what staleness/INACTIVE transitions are measured from (doc03).
        """
        now = datetime.now(UTC)
        existing = self._session.get(PropertyModel, prop.id)

        model = _to_model(prop, now=now)
        if existing is not None:
            model.first_seen_at = existing.first_seen_at

        price = prop.price
        price_changed = price is not None and self._price_changed(existing, price)

        # The property row must exist before PriceHistory is inserted, or its
        # property_id foreign key has nothing to point at yet. PropertyModel and
        # PriceHistoryModel have no ORM relationship(), so an explicit flush is
        # needed rather than relying on SQLAlchemy's automatic dependency
        # ordering between otherwise-unrelated mapped classes.
        self._session.merge(model)
        self._session.flush()

        if price_changed and price is not None:
            self._session.add(
                PriceHistoryModel(
                    id=uuid4(),
                    property_id=prop.id,
                    price_amount=price.amount,
                    price_currency=price.currency.value,
                    observed_at=now,
                )
            )

    def get(self, property_id: PropertyId) -> Property | None:
        model = self._session.get(PropertyModel, property_id)
        return _to_domain(model) if model is not None else None

    @staticmethod
    def _price_changed(existing: PropertyModel | None, price: Money) -> bool:
        if existing is None or existing.price_amount is None:
            return True
        return (
            existing.price_amount != price.amount or existing.price_currency != price.currency.value
        )
