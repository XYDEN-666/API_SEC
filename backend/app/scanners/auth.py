"""Build HTTP auth headers from a stored credential.

Shared by every scanner that sends requests, so authenticated targets are
tested as an authenticated client rather than anonymously. Decryption stays
inside this module: the plaintext value is used to build a request header and
is never placed in a finding or evidence string.
"""

import base64

from app.core.crypto import decrypt_value


def auth_headers(credential) -> dict[str, str]:
    """Return the request headers for ``credential`` (empty when ``None``).

    ``bearer`` and ``basic`` map to an ``Authorization`` header; anything else
    (including ``api_key``) is sent as ``X-API-Key``.
    """
    if credential is None:
        return {}
    value = decrypt_value(credential.encrypted_value)
    auth_type = (credential.auth_type or "").lower()
    if auth_type == "bearer":
        return {"Authorization": f"Bearer {value}"}
    if auth_type == "basic":
        encoded = base64.b64encode(value.encode("utf-8")).decode("ascii")
        return {"Authorization": f"Basic {encoded}"}
    return {"X-API-Key": value}
