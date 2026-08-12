"""Credential encryption-at-rest tests."""

import uuid

from app.core.crypto import decrypt_value, encrypt_value
from tests.helpers import (
    get_credential_encrypted_value,
    insert_credential,
)

PASSWORD = "CorrectHorse42!"


def _email(prefix: str) -> str:
    return f"test-{prefix}-{uuid.uuid4().hex}@example.com"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _register(client, email: str) -> tuple[int, str]:
    register = client.post(
        "/auth/register", json={"email": email, "password": PASSWORD}
    )
    assert register.status_code == 201
    login = client.post(
        "/auth/login", json={"email": email, "password": PASSWORD}
    )
    assert login.status_code == 200
    return register.json()["id"], login.json()["access_token"]


def _create_project_with_target(client, token: str) -> int:
    project = client.post(
        "/projects", json={"name": "Secrets Project"}, headers=_auth(token)
    )
    assert project.status_code == 201
    target = client.post(
        f"/projects/{project.json()['id']}/targets",
        json={"name": "API", "base_url": "https://api.example.com"},
        headers=_auth(token),
    )
    assert target.status_code == 201
    return target.json()["id"]


def test_encryption_round_trip() -> None:
    plaintext = "super-secret-api-key-12345"
    token = encrypt_value(plaintext)

    assert token != plaintext
    assert token.startswith("gAAAA")  # Fernet tokens always start with gAAAA
    assert decrypt_value(token) == plaintext


def test_credential_value_is_encrypted_at_rest(client) -> None:
    _, token = _register(client, _email("owner"))
    target_id = _create_project_with_target(client, token)
    plaintext = "sk-live-9876543210abcdef"

    stored = encrypt_value(plaintext)
    credential_id = insert_credential(
        target_id=target_id,
        identity_name="ci-bot",
        auth_type="api_key",
        encrypted_value=stored,
    )

    raw = get_credential_encrypted_value(credential_id)

    # The raw row must never contain the plaintext.
    assert raw == stored
    assert raw != plaintext
    assert plaintext not in raw
    assert raw.startswith("gAAAA")

    # And the stored value decrypts back to the original via the helper.
    assert decrypt_value(raw) == plaintext


def test_same_plaintext_encrypts_to_different_tokens() -> None:
    value = "same-secret-value"
    assert encrypt_value(value) != encrypt_value(value)
