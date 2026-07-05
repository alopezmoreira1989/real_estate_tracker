"""Domain entities and value objects — the canonical model.

Everything downstream of normalization speaks in these terms only
(docs/architecture/02-domain-model.md).
"""

from real_estate.domain.model.alert import SearchAlert
from real_estate.domain.model.area import Area, PricePerM2
from real_estate.domain.model.conditions import (
    AlertCondition,
    ConditionValue,
    GroupOperator,
    Operator,
    RuleGroup,
)
from real_estate.domain.model.features import Features
from real_estate.domain.model.identifiers import (
    AlertId,
    ConditionId,
    MatchId,
    PropertyId,
    UserId,
)
from real_estate.domain.model.location import GeoPoint, Location
from real_estate.domain.model.media import Media
from real_estate.domain.model.money import Money
from real_estate.domain.model.property import Property

__all__ = [
    "AlertCondition",
    "AlertId",
    "Area",
    "ConditionId",
    "ConditionValue",
    "Features",
    "GeoPoint",
    "GroupOperator",
    "Location",
    "MatchId",
    "Media",
    "Money",
    "Operator",
    "PricePerM2",
    "Property",
    "PropertyId",
    "RuleGroup",
    "SearchAlert",
    "UserId",
]
