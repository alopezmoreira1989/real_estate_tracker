import pytest
from cryptography.fernet import Fernet

from real_estate.infrastructure.persistence.encryption import (
    MissingEncryptionKeyError,
    decrypt_json,
    encrypt_json,
)


def test_encrypt_then_decrypt_round_trips() -> None:
    key = Fernet.generate_key().decode()

    token = encrypt_json({"target": "chat-42"}, key=key)
    result = decrypt_json(token, key=key)

    assert result == {"target": "chat-42"}


def test_encrypted_token_is_not_plaintext() -> None:
    key = Fernet.generate_key().decode()

    token = encrypt_json({"target": "chat-42"}, key=key)

    assert "chat-42" not in token


def test_encrypt_without_a_key_raises() -> None:
    with pytest.raises(MissingEncryptionKeyError):
        encrypt_json({"target": "chat-42"}, key=None)


def test_decrypt_without_a_key_raises() -> None:
    with pytest.raises(MissingEncryptionKeyError):
        decrypt_json("irrelevant", key=None)
