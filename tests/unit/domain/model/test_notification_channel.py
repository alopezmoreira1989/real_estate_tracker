from uuid import uuid4

from real_estate.domain.model.identifiers import NotificationChannelId, UserId
from real_estate.domain.model.notification_channel import ChannelType, NotificationChannel


def test_notification_channel_defaults_to_enabled() -> None:
    channel = NotificationChannel(
        id=NotificationChannelId(uuid4()),
        user_id=UserId(uuid4()),
        channel_type=ChannelType.TELEGRAM,
        target="123456789",
    )

    assert channel.is_enabled is True
