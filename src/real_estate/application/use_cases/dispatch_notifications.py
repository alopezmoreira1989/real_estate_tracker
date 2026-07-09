"""DispatchNotifications — polls the outbox and sends due notifications.

list PENDING -> resolve channel + build message -> rate-limit -> send ->
mark SENT/FAILED (docs/architecture/08-sequence-diagrams.md §3). A failed
delivery below ``max_attempts`` simply stays PENDING for the next scheduled
run to retry — there is no in-process retry loop; Phase 7's scheduler
provides the cadence (issue #31).
"""

from __future__ import annotations

from collections.abc import Callable

from real_estate.application.dto import DispatchReport
from real_estate.application.ports import Clock
from real_estate.domain.model.identifiers import MatchId, NotificationChannelId, NotificationId
from real_estate.domain.ports import Notifier, NotifierError, UnitOfWork
from real_estate.domain.services.notification_formatter import format_match_message


class DispatchNotifications:
    """Sends every PENDING notification, isolating one delivery failure from the rest."""

    def __init__(
        self,
        *,
        uow_factory: Callable[[], UnitOfWork],
        notifier_for_channel_type: Callable[[str], Notifier],
        rate_limit: Callable[[str], None],
        clock: Clock,
        max_attempts: int = 5,
        batch_size: int = 50,
    ) -> None:
        self._uow_factory = uow_factory
        self._notifier_for_channel_type = notifier_for_channel_type
        self._rate_limit = rate_limit
        self._clock = clock
        self._max_attempts = max_attempts
        self._batch_size = batch_size

    def run(self) -> DispatchReport:
        with self._uow_factory() as uow:
            pending = uow.notifications.list_pending(self._batch_size)

        sent = 0
        failed = 0
        for notification in pending:
            assert notification.id is not None  # persisted: always has an id
            with self._uow_factory() as uow:
                delivered = self._deliver(
                    uow, notification.id, notification.channel_id, notification.match_id
                )
                if delivered:
                    sent += 1
                else:
                    failed += 1
                uow.commit()

        return DispatchReport(notifications_pending=len(pending), sent=sent, failed=failed)

    def _deliver(
        self,
        uow: UnitOfWork,
        notification_id: NotificationId,
        channel_id: NotificationChannelId,
        match_id: MatchId,
    ) -> bool:
        channel = uow.notification_channels.get(channel_id)
        if channel is None or not channel.is_enabled:
            return False

        match = uow.matches.get(match_id)
        prop = uow.properties.get(match.property_id) if match is not None else None
        if match is None or prop is None:
            return False

        alert = uow.alerts.get(match.alert_id)
        alert_name = alert.name if alert is not None else "your alert"
        url = uow.portal_listings.get_url_for_property(prop.id)
        message = format_match_message(alert_name, prop, url)

        self._rate_limit(channel.channel_type.value)
        notifier = self._notifier_for_channel_type(channel.channel_type.value)
        now = self._clock.now()
        try:
            notifier.send(channel.target, message)
        except NotifierError as exc:
            uow.notifications.mark_failed(
                notification_id, error=str(exc), max_attempts=self._max_attempts, now=now
            )
            return False

        uow.notifications.mark_sent(notification_id, sent_at=now)
        return True
