"""Domain entities and value objects — the canonical model.

Everything downstream of normalization speaks in these terms only
(docs/architecture/02-domain-model.md).
"""

from real_estate.domain.model.area import Area, PricePerM2
from real_estate.domain.model.features import Features
from real_estate.domain.model.location import GeoPoint, Location
from real_estate.domain.model.media import Media
from real_estate.domain.model.money import Money

__all__ = [
    "Area",
    "Features",
    "GeoPoint",
    "Location",
    "Media",
    "Money",
    "PricePerM2",
]
