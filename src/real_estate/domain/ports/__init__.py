"""Domain ports — abstract interfaces implemented by infrastructure adapters.

The domain depends on these; only the composition root binds concrete
implementations (Dependency Inversion).
"""

from real_estate.domain.ports.normalizer import NormalizationIssue, NormalizationResult, Normalizer
from real_estate.domain.ports.notifier import NotificationMessage, Notifier, NotifierError
from real_estate.domain.ports.repositories import (
    AlertRepository,
    MatchRepository,
    NotificationChannelRepository,
    NotificationRepository,
    PortalListingRepository,
    PropertyRepository,
    SearchCacheRepository,
    SearchExecutionRepository,
    SearchExecutionStatus,
)
from real_estate.domain.ports.scraper import PortalQuery, RawListing, Scraper
from real_estate.domain.ports.unit_of_work import UnitOfWork

__all__ = [
    "AlertRepository",
    "MatchRepository",
    "NormalizationIssue",
    "NormalizationResult",
    "Normalizer",
    "NotificationChannelRepository",
    "NotificationMessage",
    "NotificationRepository",
    "Notifier",
    "NotifierError",
    "PortalListingRepository",
    "PortalQuery",
    "PropertyRepository",
    "RawListing",
    "Scraper",
    "SearchCacheRepository",
    "SearchExecutionRepository",
    "SearchExecutionStatus",
    "UnitOfWork",
]
