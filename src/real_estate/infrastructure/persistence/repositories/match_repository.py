"""SQLAlchemy adapter for :class:`MatchRepository`."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from real_estate.domain.model.identifiers import AlertId, MatchId, PropertyId, UserId
from real_estate.domain.model.match import AlertMatch, MatchStatus
from real_estate.infrastructure.persistence.models.orm import AlertMatchModel, SearchAlertModel


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
        return self._to_domain(model)

    def list_recent_for_user(self, user_id: UserId, *, limit: int) -> Sequence[AlertMatch]:
        stmt = (
            select(AlertMatchModel)
            .join(SearchAlertModel, SearchAlertModel.id == AlertMatchModel.alert_id)
            .where(SearchAlertModel.user_id == user_id)
            .order_by(AlertMatchModel.matched_at.desc())
            .limit(limit)
        )
        return [self._to_domain(m) for m in self._session.execute(stmt).scalars()]

    @staticmethod
    def _to_domain(model: AlertMatchModel) -> AlertMatch:
        return AlertMatch(
            alert_id=AlertId(model.alert_id),
            property_id=PropertyId(model.property_id),
            matched_at=model.matched_at,
            status=MatchStatus(model.status),
            id=MatchId(model.id),
        )
