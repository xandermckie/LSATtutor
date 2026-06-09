"""Tests for encryption and user/session CRUD."""

import os
import pytest
from cryptography.fernet import Fernet

os.environ.setdefault("FERNET_KEY", Fernet.generate_key().decode())
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-api-key")

from app.storage.encryption import decrypt_data, encrypt_data


def test_encrypt_decrypt_round_trip():
    """Encrypting then decrypting a dict returns the original data."""
    original = {"email": "test@example.com", "password_hash": "abc123", "target_exam_date": None}
    token = encrypt_data(original)
    result = decrypt_data(token)
    assert result == original


def test_encrypt_produces_bytes():
    """encrypt_data returns bytes."""
    token = encrypt_data({"key": "value"})
    assert isinstance(token, bytes)


def test_decrypt_raises_on_bad_token():
    """decrypt_data raises on corrupted ciphertext."""
    from cryptography.fernet import InvalidToken
    with pytest.raises(InvalidToken):
        decrypt_data(b"not-valid-ciphertext")
