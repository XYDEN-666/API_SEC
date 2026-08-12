"""Credential CRUD endpoint tests: masking and ownership."""

import json
import uuid

PASSWORD = "CorrectHorse42!"
SECRET = "sk-live-9f8e7d6c5b4a3210-ultra-secret-value"


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


def _create_credential(client, token: str, target_id: int, identity: str = "ci-bot"):
    return client.post(
        f"/targets/{target_id}/credentials",
        json={
            "identity_name": identity,
            "auth_type": "api_key",
            "value": SECRET,
        },
        headers=_auth(token),
    )


def test_credential_create_list_delete_masked(client) -> None:
    _, token = _register(client, _email("owner"))
    target_id = _create_project_with_target(client, token)

    created = _create_credential(client, token, target_id)
    assert created.status_code == 201
    body = created.json()
    assert body["identity_name"] == "ci-bot"
    assert body["auth_type"] == "api_key"
    assert body["masked_value"] == "••••••••"
    # The raw secret must never appear in the response, in any form.
    assert SECRET not in json.dumps(body)
    assert "value" not in body
    credential_id = body["id"]

    listed = client.get(
        f"/targets/{target_id}/credentials", headers=_auth(token)
    )
    assert listed.status_code == 200
    assert SECRET not in listed.text  # decrypted value absent from raw body
    assert "sk-live" not in listed.text
    items = listed.json()
    assert len(items) == 1
    assert items[0]["id"] == credential_id
    assert items[0]["masked_value"] == "••••••••"

    deleted = client.delete(
        f"/targets/{target_id}/credentials/{credential_id}",
        headers=_auth(token),
    )
    assert deleted.status_code == 204
    assert (
        client.get(
            f"/targets/{target_id}/credentials", headers=_auth(token)
        ).json()
        == []
    )


def test_duplicate_identity_returns_409(client) -> None:
    _, token = _register(client, _email("owner"))
    target_id = _create_project_with_target(client, token)

    assert _create_credential(client, token, target_id).status_code == 201
    assert (
        _create_credential(client, token, target_id, identity="ci-bot").status_code
        == 409
    )


def test_credentials_scoped_to_owner_and_require_auth(client) -> None:
    _, owner_token = _register(client, _email("owner"))
    _, other_token = _register(client, _email("other"))
    target_id = _create_project_with_target(client, owner_token)
    credential_id = _create_credential(client, owner_token, target_id).json()["id"]

    other_headers = _auth(other_token)
    assert (
        client.get(
            f"/targets/{target_id}/credentials", headers=other_headers
        ).status_code
        == 404
    )
    assert (
        _create_credential(client, other_token, target_id).status_code == 404
    )
    assert (
        client.delete(
            f"/targets/{target_id}/credentials/{credential_id}",
            headers=other_headers,
        ).status_code
        == 404
    )

    assert (
        client.get(f"/targets/{target_id}/credentials").status_code == 401
    )
    assert (
        client.post(
            f"/targets/{target_id}/credentials",
            json={
                "identity_name": "anon",
                "auth_type": "api_key",
                "value": "x",
            },
        ).status_code
        == 401
    )
