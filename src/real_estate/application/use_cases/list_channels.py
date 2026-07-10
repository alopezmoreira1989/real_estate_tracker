"""ListChannels — every notification channel owned by a user (enabled or not)."""

from __future__ import annotations

from collections.abc import Callable, Sequence

from real_estate.domain.model.identifiers import UserId
from real_estate.domain.model.notification_channel import NotificationChannel
from real_estate.domain.ports import UnitOfWork


class ListChannels:
    def __init__(self, *, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def run(self, *, user_id: UserId) -> Sequence[NotificationChannel]:
        with self._uow_factory() as uow:
            return uow.notification_channels.list_for_user(user_id)
