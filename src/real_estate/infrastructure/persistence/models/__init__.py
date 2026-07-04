"""ORM models. Importing this package registers every table on ``Base.metadata``
(used by Alembic autogenerate and by ``create_all`` in tests)."""

from real_estate.infrastructure.persistence.base import Base
from real_estate.infrastructure.persistence.models.orm import (
    AlertConditionModel,
    AlertMatchModel,
    AlertSubscriptionPortalModel,
    NotificationChannelModel,
    NotificationModel,
    PortalListingModel,
    PortalModel,
    PriceHistoryModel,
    PropertyModel,
    SearchAlertModel,
    SearchCacheModel,
    SearchExecutionModel,
    UserModel,
)

__all__ = [
    "AlertConditionModel",
    "AlertMatchModel",
    "AlertSubscriptionPortalModel",
    "Base",
    "NotificationChannelModel",
    "NotificationModel",
    "PortalListingModel",
    "PortalModel",
    "PriceHistoryModel",
    "PropertyModel",
    "SearchAlertModel",
    "SearchCacheModel",
    "SearchExecutionModel",
    "UserModel",
]
