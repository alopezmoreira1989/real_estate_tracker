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


class Notifier(Protocol):
    """Delivers a message to a single configured channel target."""

    channel_type: str

    def send(self, target: str, message: NotificationMessage) -> None:
        """Deliver ``message`` to ``target`` (e.g. a Telegram chat id)."""
        ...
