"""Core security primitives.

Password hashing uses bcrypt, and this module is the single source of truth
for every place a password is hashed or verified.
"""

import bcrypt


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
