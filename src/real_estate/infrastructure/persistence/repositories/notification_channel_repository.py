"""SQLAlchemy adapter for :class:`NotificationChannelRepository`.

``target`` is encrypted at rest inside ``NotificationChannelModel.config``
(CLAUDE.md §14) — the domain entity always sees the plain value.
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from real_estate.domain.model.identifiers import NotificationChannelId, UserId
from real_estate.domain.model.notification_channel import ChannelType, NotificationChannel
from real_estate.infrastructure.persistence.encryption import decrypt_json, encrypt_json
from real_estate.infrastructure.persistence.models.orm import NotificationChannelModel


class SqlAlchemyNotificationChannelRepository:
    """Persistence of a user's notification channels."""

    def __init__(self, session: Session, *, encryption_key: str | None) -> None:
        self._session = session
        self._encryption_key = encryption_key

    def add(self, channel: NotificationChannel) -> None:
        encrypted = encrypt_json({"target": channel.target}, key=self._encryption_key)
        self._session.merge(
            NotificationChannelModel(
                id=channel.id,
                user_id=channel.user_id,
                channel_type=channel.channel_type.value,
                config={"encrypted": encrypted},
                is_enabled=channel.is_enabled,
            )
        )

    def get(self, channel_id: NotificationChannelId) -> NotificationChannel | None:
        model = self._session.get(NotificationChannelModel, channel_id)
        if model is None:
            return None
        return self._to_domain(model)

    def list_enabled_for_user(self, user_id: UserId) -> Sequence[NotificationChannel]:
        models = self._session.execute(
            select(NotificationChannelModel).where(
                NotificationChannelModel.user_id == user_id,
                NotificationChannelModel.is_enabled.is_(True),
            )
        ).scalars()
        return [self._to_domain(model) for model in models]

    def _to_domain(self, model: NotificationChannelModel) -> NotificationChannel:
        config = decrypt_json(model.config["encrypted"], key=self._encryption_key)
        return NotificationChannel(
            id=NotificationChannelId(model.id),
            user_id=UserId(model.user_id),
            channel_type=ChannelType(model.channel_type),
            target=config["target"],
            is_enabled=model.is_enabled,
        )
