from __future__ import annotations

from types import TracebackType
from uuid import uuid4

from real_estate.application.use_cases.create_channel import CreateChannel
from real_estate.domain.model.identifiers import UserId
from real_estate.domain.model.notification_channel import ChannelType, NotificationChannel


class _FakeNotificationChannelRepo:
    def __init__(self) -> None:
        self.added: list[NotificationChannel] = []

    def add(self, channel: NotificationChannel) -> None:
        self.added.append(channel)


class _FakeUoW:
    def __init__(self) -> None:
        self.notification_channels = _FakeNotificationChannelRepo()
        self.committed = False

    def __enter__(self) -> _FakeUoW:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        return None

    def commit(self) -> None:
        self.committed = True


def test_creates_and_persists_a_telegram_channel() -> None:
    uow = _FakeUoW()
    use_case = CreateChannel(uow_factory=lambda: uow)

    channel = use_case.run(
        user_id=UserId(uuid4()), channel_type=ChannelType.TELEGRAM, target="chat-1"
    )

    assert uow.committed is True
    assert uow.notification_channels.added == [channel]
    assert channel.channel_type is ChannelType.TELEGRAM
    assert channel.target == "chat-1"
    assert channel.is_enabled is True
