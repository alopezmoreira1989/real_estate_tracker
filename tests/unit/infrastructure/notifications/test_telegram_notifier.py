from __future__ import annotations

import httpx
import pytest

from real_estate.domain.ports.notifier import NotificationMessage, NotifierError
from real_estate.infrastructure.notifications.telegram_notifier import TelegramNotifier


def _make_notifier(handler: object) -> TelegramNotifier:
    client = httpx.Client(transport=httpx.MockTransport(handler))  # type: ignore[arg-type]
    return TelegramNotifier("fake-token", client=client)


def test_send_posts_to_the_telegram_api_with_chat_id_and_text() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"ok": True})

    notifier = _make_notifier(handler)
    message = NotificationMessage(
        title="New match: Land in Pontevedra", body="A plot near water", url="https://x.test/1"
    )

    notifier.send("chat-42", message)

    assert len(requests) == 1
    assert requests[0].url.path == "/botfake-token/sendMessage"
    body = requests[0].content.decode()
    assert '"chat_id":"chat-42"' in body
    assert "New match: Land in Pontevedra" in body
    assert "https://x.test/1" in body


def test_send_raises_notifier_error_on_a_non_2xx_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"ok": False, "description": "chat not found"})

    notifier = _make_notifier(handler)
    message = NotificationMessage(title="t", body="b")

    with pytest.raises(NotifierError):
        notifier.send("bad-chat", message)
