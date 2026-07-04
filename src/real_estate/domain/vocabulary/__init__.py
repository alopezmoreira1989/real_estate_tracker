"""Controlled vocabularies for the canonical domain model.

Portal-specific free text is mapped onto these controlled values by the
normalization layer, so downstream code never sees portal spellings.
"""

from real_estate.domain.vocabulary.currency import Currency
from real_estate.domain.vocabulary.geography import Municipality, Province
from real_estate.domain.vocabulary.listing import ListingStatus, ListingType
from real_estate.domain.vocabulary.property_kind import LandType, PropertyType

__all__ = [
    "Currency",
    "LandType",
    "ListingStatus",
    "ListingType",
    "Municipality",
    "Province",
    "PropertyType",
]
