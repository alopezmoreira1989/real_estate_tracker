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
    NotificationChannelId,
    NotificationId,
    PropertyId,
    UserId,
)
from real_estate.domain.model.location import GeoPoint, Location
from real_estate.domain.model.match import AlertMatch, MatchStatus
from real_estate.domain.model.media import Media
from real_estate.domain.model.money import Money
from real_estate.domain.model.notification import Notification, NotificationStatus
from real_estate.domain.model.notification_channel import ChannelType, NotificationChannel
from real_estate.domain.model.property import Property
from real_estate.domain.model.search_execution import SearchExecution, SearchExecutionStatus

__all__ = [
    "AlertCondition",
    "AlertId",
    "AlertMatch",
    "Area",
    "ChannelType",
    "ConditionId",
    "ConditionValue",
    "Features",
    "GeoPoint",
    "GroupOperator",
    "Location",
    "MatchId",
    "MatchStatus",
    "Media",
    "Money",
    "Notification",
    "NotificationChannel",
    "NotificationChannelId",
    "NotificationId",
    "NotificationStatus",
    "Operator",
    "PricePerM2",
    "Property",
    "PropertyId",
    "RuleGroup",
    "SearchAlert",
    "SearchExecution",
    "SearchExecutionStatus",
    "UserId",
]
