"""e2e: DispatchNotifications against a real (temp) SQLite DB — only the
Notifier is faked (no real network), matching issue #31's acceptance
criteria: PENDING -> SENT on success; attempts/last_error on failure;
respects per-channel rate limits.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from real_estate.application.use_cases.dispatch_notifications import DispatchNotifications
from real_estate.domain.model import (
    AlertCondition,
    AlertId,
    Area,
    ChannelType,
    Features,
    GroupOperator,
    Location,
    Media,
    Money,
    NotificationChannel,
    NotificationChannelId,
    Operator,
    Property,
    PropertyId,
    RuleGroup,
    SearchAlert,
)
from real_estate.domain.model.match import AlertMatch
from real_estate.domain.ports.notifier import NotificationMessage, NotifierError
from real_estate.domain.vocabulary import ListingStatus, ListingType, PropertyType, Province

NOW = datetime(2026, 7, 9, 12, 0)  # naive: SQLite does not persist tz


@dataclass
class _FixedClock:
    _now: datetime

    def now(self) -> datetime:
        return self._now


class _FakeNotifier:
    channel_type = "TELEGRAM"

    def __init__(self, *, error: Exception | None = None) -> None:
        self._error = error
        self.sent: list[tuple[str, NotificationMessage]] = []

    def send(self, target: str, message: NotificationMessage) -> None:
        if self._error is not None:
            raise self._error
        self.sent.append((target, message))


@dataclass
class _RecordingRateLimiter:
    calls: list[str] = field(default_factory=list)

    def __call__(self, channel_type: str) -> None:
        self.calls.append(channel_type)


def _seed_pending_notification(persistence, *, target: str = "chat-1") -> NotificationChannelId:
    """Insert a Property + SearchAlert + AlertMatch + enabled channel, and rely
    on RunAlertCycle's enqueue behaviour by enqueueing directly (this test
    exercises the dispatcher, not the enqueue path — already covered by
    Phase 6's #29 tests)."""
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
    channel = NotificationChannel(
        id=NotificationChannelId(uuid4()),
        user_id=persistence.user_id,
        channel_type=ChannelType.TELEGRAM,
        target=target,
    )
    with persistence.new_uow() as uow:
        uow.properties.add(prop)
        uow.alerts.add(alert)
        uow.notification_channels.add(channel)
        uow.portal_listings.upsert(
            portal_slug="idealista",
            external_id="ext-1",
            property_id=prop.id,
            url="https://idealista.com/ext-1",
            raw_payload={},
            content_hash="hash-a",
            scraped_at=NOW,
        )
        match_id = uow.matches.add_if_new(
            AlertMatch(alert_id=alert.id, property_id=prop.id, matched_at=NOW)
        )
        assert match_id is not None
        uow.notifications.enqueue(match_id, channel.id, now=NOW)
        uow.commit()
    return channel.id


def _make_dispatcher(
    persistence,
    notifier: _FakeNotifier,
    *,
    rate_limit: _RecordingRateLimiter | None = None,
    max_attempts: int = 5,
) -> DispatchNotifications:
    limiter = rate_limit or _RecordingRateLimiter()
    return DispatchNotifications(
        uow_factory=persistence.new_uow,
        notifier_for_channel_type=lambda _channel_type: notifier,
        rate_limit=limiter,
        clock=_FixedClock(NOW),
        max_attempts=max_attempts,
    )


def test_a_pending_notification_is_sent_and_marked_sent(persistence) -> None:
    _seed_pending_notification(persistence, target="chat-1")
    notifier = _FakeNotifier()
    dispatcher = _make_dispatcher(persistence, notifier)

    report = dispatcher.run()

    assert report.notifications_pending == 1
    assert report.sent == 1
    assert report.failed == 0
    assert len(notifier.sent) == 1
    target, message = notifier.sent[0]
    assert target == "chat-1"
    assert "Land in Pontevedra" in message.title
    assert "60,000 EUR" in message.body
    assert "3,000 m²" in message.body
    assert message.url == "https://idealista.com/ext-1"

    with persistence.new_uow() as uow:
        assert uow.notifications.list_pending(limit=10) == []


def test_rate_limit_is_invoked_with_the_channel_type(persistence) -> None:
    _seed_pending_notification(persistence)
    notifier = _FakeNotifier()
    limiter = _RecordingRateLimiter()
    dispatcher = _make_dispatcher(persistence, notifier, rate_limit=limiter)

    dispatcher.run()

    assert limiter.calls == ["TELEGRAM"]


def test_a_failed_delivery_below_max_attempts_stays_pending(persistence) -> None:
    _seed_pending_notification(persistence)
    notifier = _FakeNotifier(error=NotifierError("telegram unreachable"))
    dispatcher = _make_dispatcher(persistence, notifier, max_attempts=3)

    report = dispatcher.run()

    assert report.sent == 0
    assert report.failed == 1
    with persistence.new_uow() as uow:
        [still_pending] = uow.notifications.list_pending(limit=10)
    assert still_pending.attempts == 1
    assert still_pending.last_error == "telegram unreachable"


def test_a_failed_delivery_at_max_attempts_transitions_to_failed(persistence) -> None:
    _seed_pending_notification(persistence)
    notifier = _FakeNotifier(error=NotifierError("telegram unreachable"))
    dispatcher = _make_dispatcher(persistence, notifier, max_attempts=1)

    dispatcher.run()

    with persistence.new_uow() as uow:
        assert uow.notifications.list_pending(limit=10) == []


def test_a_disabled_channel_is_skipped_and_left_pending(persistence) -> None:
    channel_id = _seed_pending_notification(persistence)
    with persistence.new_uow() as uow:
        channel = uow.notification_channels.get(channel_id)
        assert channel is not None
        disabled = NotificationChannel(
            id=channel.id,
            user_id=channel.user_id,
            channel_type=channel.channel_type,
            target=channel.target,
            is_enabled=False,
        )
        uow.notification_channels.add(disabled)
        uow.commit()

    notifier = _FakeNotifier()
    dispatcher = _make_dispatcher(persistence, notifier)

    report = dispatcher.run()

    assert report.sent == 0
    assert report.failed == 1
    assert notifier.sent == []
    with persistence.new_uow() as uow:
        assert len(uow.notifications.list_pending(limit=10)) == 1
