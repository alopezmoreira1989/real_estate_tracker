"""SQLAlchemy adapter for :class:`MatchRepository`."""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from real_estate.domain.model.match import AlertMatch
from real_estate.infrastructure.persistence.models.orm import AlertMatchModel


class SqlAlchemyMatchRepository:
    """Idempotent persistence of matches via the ``UNIQUE(alert_id, property_id)`` constraint."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add_if_new(self, match: AlertMatch) -> bool:
        existing = self._session.execute(
            select(AlertMatchModel).where(
                AlertMatchModel.alert_id == match.alert_id,
                AlertMatchModel.property_id == match.property_id,
            )
        ).scalar_one_or_none()
        if existing is not None:
            return False

        self._session.add(
            AlertMatchModel(
                id=uuid4(),
                alert_id=match.alert_id,
                property_id=match.property_id,
                matched_at=match.matched_at,
                status=match.status.value,
            )
        )
        return True
