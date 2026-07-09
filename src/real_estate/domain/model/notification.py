"""Notification: one outbox entry — a match queued for delivery on a channel."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from real_estate.domain.model.identifiers import MatchId, NotificationChannelId, NotificationId


class NotificationStatus(StrEnum):
    """Lifecycle of an outbox entry (doc03, doc08 §3)."""

    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class Notification:
    """A single delivery attempt record for one ``(match, channel)`` pair.

    Identity is the natural key ``(match_id, channel_id)`` — enqueueing is
    idempotent, mirroring how :class:`~real_estate.domain.model.match.AlertMatch`
    is keyed by ``(alert_id, property_id)``.
    """

    match_id: MatchId
    channel_id: NotificationChannelId
    created_at: datetime = field(compare=False)
    status: NotificationStatus = field(default=NotificationStatus.PENDING, compare=False)
    attempts: int = field(default=0, compare=False)
    last_error: str | None = field(default=None, compare=False)
    sent_at: datetime | None = field(default=None, compare=False)
    id: NotificationId | None = field(default=None, compare=False)
