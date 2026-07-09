"""Fernet-based encryption for notification channel secrets at rest (CLAUDE.md §14).

Used only by :class:`~real_estate.infrastructure.persistence.repositories.
notification_channel_repository.SqlAlchemyNotificationChannelRepository` — the
domain never sees ciphertext.
"""

from __future__ import annotations

import json
from typing import Any

from cryptography.fernet import Fernet


class MissingEncryptionKeyError(RuntimeError):
    """Raised when ``NOTIFICATION_ENCRYPTION_KEY`` is not configured."""


def encrypt_json(data: dict[str, Any], *, key: str | None) -> str:
    """Serialize ``data`` to JSON and encrypt it with ``key``."""
    if not key:
        raise MissingEncryptionKeyError("NOTIFICATION_ENCRYPTION_KEY is not configured")
    token = Fernet(key.encode()).encrypt(json.dumps(data).encode())
    return token.decode()


def decrypt_json(token: str, *, key: str | None) -> dict[str, Any]:
    """Decrypt ``token`` and deserialize it back to a dict."""
    if not key:
        raise MissingEncryptionKeyError("NOTIFICATION_ENCRYPTION_KEY is not configured")
    payload = Fernet(key.encode()).decrypt(token.encode())
    result: dict[str, Any] = json.loads(payload.decode())
    return result
