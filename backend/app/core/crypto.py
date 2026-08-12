"""Symmetric encryption helpers for credentials (Fernet)."""

from cryptography.fernet import Fernet

from app.core.config import settings

_fernet = Fernet(settings.encryption_key.encode("utf-8"))


def encrypt_value(plaintext: str) -> str:
    """Encrypt a plaintext value and return the Fernet token string."""
    return _fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_value(token: str) -> str:
    """Decrypt a Fernet token produced by :func:`encrypt_value`."""
    return _fernet.decrypt(token.encode("utf-8")).decode("utf-8")
