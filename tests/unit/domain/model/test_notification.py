from datetime import datetime
from uuid import uuid4

from real_estate.domain.model.identifiers import MatchId, NotificationChannelId
from real_estate.domain.model.notification import Notification, NotificationStatus

NOW = datetime(2026, 7, 9, 12, 0)


def test_notification_defaults_to_pending_with_zero_attempts() -> None:
    notification = Notification(
        match_id=MatchId(uuid4()), channel_id=NotificationChannelId(uuid4()), created_at=NOW
    )

    assert notification.status is NotificationStatus.PENDING
    assert notification.attempts == 0
    assert notification.last_error is None
    assert notification.sent_at is None


def test_notification_identity_is_the_match_channel_pair() -> None:
    match_id = MatchId(uuid4())
    channel_id = NotificationChannelId(uuid4())

    first = Notification(match_id=match_id, channel_id=channel_id, created_at=NOW, attempts=0)
    second = Notification(match_id=match_id, channel_id=channel_id, created_at=NOW, attempts=3)

    assert first == second
