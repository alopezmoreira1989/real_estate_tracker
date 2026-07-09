"""Integration tests: the notification outbox + channel repositories, against
a real (temp) SQLite DB — including the encrypt/decrypt round trip.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from real_estate.domain.model import (
    AlertCondition,
    AlertId,
    Area,
    Features,
    GroupOperator,
    Location,
    Media,
    Money,
    Operator,
    Property,
    PropertyId,
    RuleGroup,
    SearchAlert,
)
from real_estate.domain.model.identifiers import MatchId, NotificationChannelId
from real_estate.domain.model.match import AlertMatch
from real_estate.domain.model.notification_channel import ChannelType, NotificationChannel
from real_estate.domain.vocabulary import ListingStatus, ListingType, PropertyType, Province

NOW = datetime(2026, 7, 9, 12, 0)  # naive: SQLite does not persist tz


def _channel(user_id, target: str = "123456789") -> NotificationChannel:
    return NotificationChannel(
        id=NotificationChannelId(uuid4()),
        user_id=user_id,
        channel_type=ChannelType.TELEGRAM,
        target=target,
    )


def _persisted_match_id(persistence) -> MatchId:
    """Insert a Property + SearchAlert + AlertMatch and return the match's real id
    (``notifications.match_id`` has a foreign key onto ``alert_matches.id``)."""
    prop = Property(
        id=PropertyId(uuid4()),
        listing_type=ListingType.SALE,
        property_type=PropertyType.LAND,
        location=Location(province=Province.PONTEVEDRA),
        title="Urbanizable plot near water",
        status=ListingStatus.ACTIVE,
        price=Money(Decimal("60000")),
        area=Area(Decimal("3000")),
        features=Features(),
        media=Media(),
    )
    alert = SearchAlert.create(
        id=AlertId(uuid4()),
        user_id=persistence.user_id,
        name="Land in Pontevedra",
        portal_slugs=frozenset({"idealista"}),
        frequency_seconds=900,
        conditions=RuleGroup(GroupOperator.ALL, (AlertCondition("province", Operator.EQ, "36"),)),
        now=NOW,
    )
    with persistence.new_uow() as uow:
        uow.properties.add(prop)
        uow.alerts.add(alert)
        match_id = uow.matches.add_if_new(
            AlertMatch(alert_id=alert.id, property_id=prop.id, matched_at=NOW)
        )
        uow.commit()
    assert match_id is not None
    return match_id


def test_notification_channel_round_trips_the_encrypted_target(persistence) -> None:
    channel = _channel(persistence.user_id, target="chat-42")
    with persistence.new_uow() as uow:
        uow.notification_channels.add(channel)
        uow.commit()

    with persistence.new_uow() as uow:
        fetched = uow.notification_channels.get(channel.id)

    assert fetched is not None
    assert fetched.target == "chat-42"
    assert fetched.channel_type == ChannelType.TELEGRAM


def test_notification_channel_list_enabled_for_user_excludes_disabled(persistence) -> None:
    enabled = _channel(persistence.user_id, target="chat-a")
    disabled = NotificationChannel(
        id=NotificationChannelId(uuid4()),
        user_id=persistence.user_id,
        channel_type=ChannelType.TELEGRAM,
        target="chat-b",
        is_enabled=False,
    )
    with persistence.new_uow() as uow:
        uow.notification_channels.add(enabled)
        uow.notification_channels.add(disabled)
        uow.commit()

    with persistence.new_uow() as uow:
        channels = uow.notification_channels.list_enabled_for_user(persistence.user_id)

    assert [c.id for c in channels] == [enabled.id]


def test_notification_channel_list_for_user_includes_disabled(persistence) -> None:
    enabled = _channel(persistence.user_id, target="chat-a")
    disabled = NotificationChannel(
        id=NotificationChannelId(uuid4()),
        user_id=persistence.user_id,
        channel_type=ChannelType.TELEGRAM,
        target="chat-b",
        is_enabled=False,
    )
    with persistence.new_uow() as uow:
        uow.notification_channels.add(enabled)
        uow.notification_channels.add(disabled)
        uow.commit()

    with persistence.new_uow() as uow:
        channels = uow.notification_channels.list_for_user(persistence.user_id)

    assert {c.id for c in channels} == {enabled.id, disabled.id}


def test_notification_enqueue_is_idempotent(persistence) -> None:
    channel = _channel(persistence.user_id)
    with persistence.new_uow() as uow:
        uow.notification_channels.add(channel)
        uow.commit()
    match_id = _persisted_match_id(persistence)

    with persistence.new_uow() as uow:
        first = uow.notifications.enqueue(match_id, channel.id, now=NOW)
        second = uow.notifications.enqueue(match_id, channel.id, now=NOW)
        uow.commit()

    assert first is True
    assert second is False

    with persistence.new_uow() as uow:
        pending = uow.notifications.list_pending(limit=10)

    assert len(pending) == 1
    assert pending[0].match_id == match_id


def test_notification_mark_sent_transitions_out_of_pending(persistence) -> None:
    channel = _channel(persistence.user_id)
    with persistence.new_uow() as uow:
        uow.notification_channels.add(channel)
        uow.commit()
    match_id = _persisted_match_id(persistence)

    with persistence.new_uow() as uow:
        uow.notifications.enqueue(match_id, channel.id, now=NOW)
        uow.commit()

    with persistence.new_uow() as uow:
        [notification] = uow.notifications.list_pending(limit=10)
        assert notification.id is not None
        uow.notifications.mark_sent(notification.id, sent_at=NOW)
        uow.commit()

    with persistence.new_uow() as uow:
        assert uow.notifications.list_pending(limit=10) == []


def test_notification_mark_failed_stays_pending_below_max_attempts(persistence) -> None:
    channel = _channel(persistence.user_id)
    with persistence.new_uow() as uow:
        uow.notification_channels.add(channel)
        uow.commit()
    match_id = _persisted_match_id(persistence)

    with persistence.new_uow() as uow:
        uow.notifications.enqueue(match_id, channel.id, now=NOW)
        uow.commit()

    with persistence.new_uow() as uow:
        [notification] = uow.notifications.list_pending(limit=10)
        assert notification.id is not None
        uow.notifications.mark_failed(notification.id, error="boom", max_attempts=3, now=NOW)
        uow.commit()

    with persistence.new_uow() as uow:
        [still_pending] = uow.notifications.list_pending(limit=10)

    assert still_pending.attempts == 1
    assert still_pending.last_error == "boom"


def test_notification_mark_failed_transitions_to_failed_at_max_attempts(persistence) -> None:
    channel = _channel(persistence.user_id)
    with persistence.new_uow() as uow:
        uow.notification_channels.add(channel)
        uow.commit()
    match_id = _persisted_match_id(persistence)

    with persistence.new_uow() as uow:
        uow.notifications.enqueue(match_id, channel.id, now=NOW)
        uow.commit()

    with persistence.new_uow() as uow:
        [notification] = uow.notifications.list_pending(limit=10)
        assert notification.id is not None
        uow.notifications.mark_failed(notification.id, error="boom", max_attempts=1, now=NOW)
        uow.commit()

    with persistence.new_uow() as uow:
        assert uow.notifications.list_pending(limit=10) == []
