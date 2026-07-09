"""SQLAlchemy adapter for :class:`MatchRepository`."""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from real_estate.domain.model.identifiers import AlertId, MatchId, PropertyId
from real_estate.domain.model.match import AlertMatch, MatchStatus
from real_estate.infrastructure.persistence.models.orm import AlertMatchModel


class SqlAlchemyMatchRepository:
    """Idempotent persistence of matches via the ``UNIQUE(alert_id, property_id)`` constraint."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add_if_new(self, match: AlertMatch) -> MatchId | None:
        existing = self._session.execute(
            select(AlertMatchModel).where(
                AlertMatchModel.alert_id == match.alert_id,
                AlertMatchModel.property_id == match.property_id,
            )
        ).scalar_one_or_none()
        if existing is not None:
            return None

        new_id = uuid4()
        self._session.add(
            AlertMatchModel(
                id=new_id,
                alert_id=match.alert_id,
                property_id=match.property_id,
                matched_at=match.matched_at,
                status=match.status.value,
            )
        )
        return MatchId(new_id)

    def get(self, match_id: MatchId) -> AlertMatch | None:
        model = self._session.get(AlertMatchModel, match_id)
        if model is None:
            return None
        return AlertMatch(
            alert_id=AlertId(model.alert_id),
            property_id=PropertyId(model.property_id),
            matched_at=model.matched_at,
            status=MatchStatus(model.status),
            id=MatchId(model.id),
        )
