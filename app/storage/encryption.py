"""Encryption helpers — all user data passes through these before hitting disk."""

import json

from app.extensions import get_fernet


def encrypt_data(data: dict) -> bytes:
    """Serialize a dict to JSON and encrypt it with Fernet.

    Args:
        data: The dict to encrypt.

    Returns:
        Encrypted bytes ready to write to disk.

    Raises:
        EnvironmentError: If FERNET_KEY is missing.
        TypeError: If data is not JSON-serializable.
    """
    fernet = get_fernet()
    raw = json.dumps(data).encode("utf-8")
    return fernet.encrypt(raw)


def decrypt_data(token: bytes) -> dict:
    """Decrypt Fernet-encrypted bytes and deserialize to a dict.

    Args:
        token: Encrypted bytes read from disk.

    Returns:
        The original dict.

    Raises:
        EnvironmentError: If FERNET_KEY is missing.
        cryptography.fernet.InvalidToken: If the token is corrupt or the key is wrong.
        json.JSONDecodeError: If the decrypted bytes are not valid JSON.
    """
    fernet = get_fernet()
    raw = fernet.decrypt(token)
    return json.loads(raw.decode("utf-8"))
