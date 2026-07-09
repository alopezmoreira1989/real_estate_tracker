"""NotificationChannel: a user's configured delivery target."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from real_estate.domain.model.identifiers import NotificationChannelId, UserId


class ChannelType(StrEnum):
    """Delivery mechanisms a notification can be sent through."""

    TELEGRAM = "TELEGRAM"


@dataclass(frozen=True, slots=True)
class NotificationChannel:
    """A single delivery target owned by a user.

    ``target`` is the plain, decrypted value (e.g. a Telegram chat id) —
    encryption at rest is an infrastructure concern applied at the repository
    boundary; the domain never handles ciphertext (CLAUDE.md §14).
    """

    id: NotificationChannelId
    user_id: UserId
    channel_type: ChannelType
    target: str
    is_enabled: bool = True
