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
from real_estate.infrastructure.persistence.repositories.property_repository import (
    SqlAlchemyPropertyRepository,
)


class SqlAlchemyUnitOfWork:
    """A single atomic transaction exposing the repositories it governs."""

    alerts: SqlAlchemyAlertRepository
    properties: SqlAlchemyPropertyRepository

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def __enter__(self) -> SqlAlchemyUnitOfWork:
        self._session = self._session_factory()
        self.alerts = SqlAlchemyAlertRepository(self._session)
        self.properties = SqlAlchemyPropertyRepository(self._session)
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
