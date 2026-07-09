"""SQLAlchemy adapter for :class:`NotificationRepository` — the notification outbox."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from real_estate.domain.model.identifiers import MatchId, NotificationChannelId, NotificationId
from real_estate.domain.model.notification import Notification, NotificationStatus
from real_estate.infrastructure.persistence.models.orm import NotificationModel


class SqlAlchemyNotificationRepository:
    """Idempotent persistence of the notification outbox (doc03, doc08 §3)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def enqueue(
        self, match_id: MatchId, channel_id: NotificationChannelId, *, now: datetime
    ) -> bool:
        existing = self._session.execute(
            select(NotificationModel).where(
                NotificationModel.match_id == match_id,
                NotificationModel.channel_id == channel_id,
            )
        ).scalar_one_or_none()
        if existing is not None:
            return False

        self._session.add(
            NotificationModel(
                id=uuid4(),
                match_id=match_id,
                channel_id=channel_id,
                status=NotificationStatus.PENDING.value,
                attempts=0,
                created_at=now,
            )
        )
        return True

    def list_pending(self, limit: int) -> Sequence[Notification]:
        models = self._session.execute(
            select(NotificationModel)
            .where(NotificationModel.status == NotificationStatus.PENDING.value)
            .order_by(NotificationModel.created_at)
            .limit(limit)
        ).scalars()
        return [self._to_domain(model) for model in models]

    def mark_sent(self, notification_id: NotificationId, *, sent_at: datetime) -> None:
        model = self._session.get(NotificationModel, notification_id)
        if model is None:
            return
        model.status = NotificationStatus.SENT.value
        model.sent_at = sent_at

    def mark_failed(
        self,
        notification_id: NotificationId,
        *,
        error: str,
        max_attempts: int,
        now: datetime,
    ) -> None:
        model = self._session.get(NotificationModel, notification_id)
        if model is None:
            return
        model.attempts += 1
        model.last_error = error
        if model.attempts >= max_attempts:
            model.status = NotificationStatus.FAILED.value

    @staticmethod
    def _to_domain(model: NotificationModel) -> Notification:
        return Notification(
            match_id=MatchId(model.match_id),
            channel_id=NotificationChannelId(model.channel_id),
            created_at=model.created_at,
            status=NotificationStatus(model.status),
            attempts=model.attempts,
            last_error=model.last_error,
            sent_at=model.sent_at,
            id=NotificationId(model.id),
        )
