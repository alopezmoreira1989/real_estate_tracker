"""SQLAlchemy Unit of Work: the transaction boundary per use-case (doc 03).

Opens a session on ``__enter__`` and exposes the repositories that share it, so
everything a use-case does commits or rolls back together. On exit any
uncommitted work is rolled back.
"""

from __future__ import annotations

from types import TracebackType

from sqlalchemy.orm import Session, sessionmaker

from real_estate.infrastructure.persistence.repositories.alert_repository import (
    SqlAlchemyAlertRepository,
)
from real_estate.infrastructure.persistence.repositories.match_repository import (
    SqlAlchemyMatchRepository,
)
from real_estate.infrastructure.persistence.repositories.notification_channel_repository import (
    SqlAlchemyNotificationChannelRepository,
)
from real_estate.infrastructure.persistence.repositories.notification_repository import (
    SqlAlchemyNotificationRepository,
)
from real_estate.infrastructure.persistence.repositories.portal_listing_repository import (
    SqlAlchemyPortalListingRepository,
)
from real_estate.infrastructure.persistence.repositories.property_repository import (
    SqlAlchemyPropertyRepository,
)
from real_estate.infrastructure.persistence.repositories.search_cache_repository import (
    SqlAlchemySearchCacheRepository,
)
from real_estate.infrastructure.persistence.repositories.search_execution_repository import (
    SqlAlchemySearchExecutionRepository,
)


class SqlAlchemyUnitOfWork:
    """A single atomic transaction exposing the repositories it governs."""

    alerts: SqlAlchemyAlertRepository
    properties: SqlAlchemyPropertyRepository
    matches: SqlAlchemyMatchRepository
    portal_listings: SqlAlchemyPortalListingRepository
    search_cache: SqlAlchemySearchCacheRepository
    search_executions: SqlAlchemySearchExecutionRepository
    notification_channels: SqlAlchemyNotificationChannelRepository
    notifications: SqlAlchemyNotificationRepository

    def __init__(
        self, session_factory: sessionmaker[Session], *, encryption_key: str | None = None
    ) -> None:
        self._session_factory = session_factory
        self._encryption_key = encryption_key

    def __enter__(self) -> SqlAlchemyUnitOfWork:
        self._session = self._session_factory()
        self.alerts = SqlAlchemyAlertRepository(self._session)
        self.properties = SqlAlchemyPropertyRepository(self._session)
        self.matches = SqlAlchemyMatchRepository(self._session)
        self.portal_listings = SqlAlchemyPortalListingRepository(self._session)
        self.search_cache = SqlAlchemySearchCacheRepository(self._session)
        self.search_executions = SqlAlchemySearchExecutionRepository(self._session)
        self.notification_channels = SqlAlchemyNotificationChannelRepository(
            self._session, encryption_key=self._encryption_key
        )
        self.notifications = SqlAlchemyNotificationRepository(self._session)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.rollback()
        self._session.close()

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()
