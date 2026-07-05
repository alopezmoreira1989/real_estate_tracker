"""Domain ports — abstract interfaces implemented by infrastructure adapters.

The domain depends on these; only the composition root binds concrete
implementations (Dependency Inversion).
"""

from real_estate.domain.ports.normalizer import Normalizer
from real_estate.domain.ports.notifier import NotificationMessage, Notifier
from real_estate.domain.ports.repositories import AlertRepository, PropertyRepository
from real_estate.domain.ports.scraper import PortalQuery, RawListing, Scraper
from real_estate.domain.ports.unit_of_work import UnitOfWork

__all__ = [
    "AlertRepository",
    "Normalizer",
    "NotificationMessage",
    "Notifier",
    "PortalQuery",
    "PropertyRepository",
    "RawListing",
    "Scraper",
    "UnitOfWork",
]
