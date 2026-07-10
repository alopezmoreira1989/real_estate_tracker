"""CreateChannel — builds and persists a new NotificationChannel."""

from __future__ import annotations

from collections.abc import Callable
from uuid import uuid4

from real_estate.domain.model.identifiers import NotificationChannelId, UserId
from real_estate.domain.model.notification_channel import ChannelType, NotificationChannel
from real_estate.domain.ports import UnitOfWork


class CreateChannel:
    """Persists a new notification channel for a user."""

    def __init__(self, *, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def run(
        self, *, user_id: UserId, channel_type: ChannelType, target: str
    ) -> NotificationChannel:
        channel = NotificationChannel(
            id=NotificationChannelId(uuid4()),
            user_id=user_id,
            channel_type=channel_type,
            target=target,
        )
        with self._uow_factory() as uow:
            uow.notification_channels.add(channel)
            uow.commit()
        return channel
