"""TelegramNotifier — sends a NotificationMessage via a plain httpx POST to the
Telegram Bot API (docs/architecture/01-architecture.md §7 supersession: no
python-telegram-bot dependency, consistent with IdealistaScraper's own use of
httpx — synchronous, no new async runtime to manage).
"""

from __future__ import annotations

import httpx

from real_estate.domain.ports.notifier import NotificationMessage

_TELEGRAM_API_BASE = "https://api.telegram.org"


class TelegramNotifier:
    """Delivers a message to a Telegram chat via the Bot API's sendMessage endpoint."""

    channel_type = "TELEGRAM"

    def __init__(self, bot_token: str, *, client: httpx.Client | None = None) -> None:
        self._bot_token = bot_token
        self._client = client or httpx.Client(timeout=10.0)

    def send(self, target: str, message: NotificationMessage) -> None:
        """Post ``message`` to the Telegram chat id ``target``.

        Raises ``httpx.HTTPStatusError`` on a non-2xx response, or another
        ``httpx.HTTPError`` on a transport failure — the dispatcher catches
        these to record a failed delivery attempt (issue #30).
        """
        response = self._client.post(
            f"{_TELEGRAM_API_BASE}/bot{self._bot_token}/sendMessage",
            json={"chat_id": target, "text": _format_text(message)},
        )
        response.raise_for_status()


def _format_text(message: NotificationMessage) -> str:
    parts = [message.title, message.body]
    if message.url is not None:
        parts.append(message.url)
    return "\n\n".join(parts)
