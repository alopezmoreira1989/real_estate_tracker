"""Notifier port and its message DTO.

Notification delivery is decoupled from scraping/matching (driver D4). A
``Notifier`` sends a channel-agnostic message; concrete adapters (Telegram,
email, …) translate it to their protocol.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class NotificationMessage:
    """A channel-agnostic message describing a matched listing."""

    title: str
    body: str
    url: str | None = None


class NotifierError(Exception):
    """A channel-agnostic delivery failure.

    Adapters wrap their transport-specific errors (e.g. ``httpx.HTTPError``)
    into this at the port boundary (CLAUDE.md §12), so callers like
    ``DispatchNotifications`` catch one domain-meaningful type instead of
    depending on any adapter's third-party exception hierarchy.
    """


class Notifier(Protocol):
    """Delivers a message to a single configured channel target."""

    channel_type: str

    def send(self, target: str, message: NotificationMessage) -> None:
        """Deliver ``message`` to ``target`` (e.g. a Telegram chat id).

        Raises :class:`NotifierError` on failure.
        """
        ...
