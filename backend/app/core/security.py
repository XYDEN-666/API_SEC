"""Core security primitives.

Password hashing uses bcrypt, and JWT creation/decoding uses PyJWT. This
module is the single source of truth for every place a password or token is
handled.
"""

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    """Hash a plaintext password with bcrypt and return the encoded hash."""
    if not isinstance(password, str):
        raise TypeError("password must be a string")
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """Return True if ``password`` matches the stored bcrypt ``hashed`` value."""
    if not isinstance(password, str) or not isinstance(hashed, str):
        return False
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"),
            hashed.encode("utf-8"),
        )
    except (ValueError, TypeError):
        # Invalid salt/hash format — treat as a failed verification.
        return False


def create_access_token(subject: int, expires_minutes: int | None = None) -> str:
    """Create a signed JWT access token for the given user id."""
    now = datetime.now(timezone.utc)
    expires = now + timedelta(
        minutes=expires_minutes or settings.access_token_expire_minutes
    )
    payload = {"sub": str(subject), "iat": now, "exp": expires}
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    """Decode and verify a JWT access token; raises on invalid/expired tokens."""
    return jwt.decode(token, settings.secret_key, algorithms=["HS256"])
