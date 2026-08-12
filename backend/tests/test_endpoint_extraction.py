"""Endpoint extraction and storage tests."""

import json
import uuid

SAMPLE_SPEC = {
    "openapi": "3.0.3",
    "info": {"title": "Sample API", "version": "1.0.0"},
    "paths": {
        "/users": {
            "get": {
                "parameters": [{"name": "limit", "in": "query"}],
                "responses": {"200": {"description": "ok"}},
            },
            "post": {"responses": {"201": {"description": "created"}}},
        },
        "/users/{user_id}": {
            "parameters": [
                {"name": "user_id", "in": "path", "required": True}
            ],
            "get": {"responses": {"200": {"description": "ok"}}},
            "put": {"responses": {"200": {"description": "ok"}}},
            "delete": {"responses": {"204": {"description": "gone"}}},
        },
    },
}

EXPECTED_ENDPOINTS = {
    ("/users", "GET"),
    ("/users", "POST"),
    ("/users/{user_id}", "GET"),
    ("/users/{user_id}", "PUT"),
    ("/users/{user_id}", "DELETE"),
}

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
        "/projects", json={"name": "Sample Project"}, headers=_auth(token)
    )
    assert project.status_code == 201
    target = client.post(
        f"/projects/{project.json()['id']}/targets",
        json={"name": "API", "base_url": "https://api.example.com"},
        headers=_auth(token),
    )
    assert target.status_code == 201
    return target.json()["id"]


def _upload_spec(client, token: str, target_id: int):
    return client.post(
        f"/targets/{target_id}/import-openapi",
        files={
            "file": (
                "openapi.json",
                json.dumps(SAMPLE_SPEC).encode(),
                "application/json",
            )
        },
        headers=_auth(token),
    )


def test_upload_persists_exactly_n_endpoints(client) -> None:
    _, token = _register(client, _email("owner"))
    target_id = _create_project_with_target(client, token)

    upload = _upload_spec(client, token, target_id)
    assert upload.status_code == 200
    assert upload.json()["endpoints_count"] == len(EXPECTED_ENDPOINTS)

    listed = client.get(
        f"/targets/{target_id}/endpoints", headers=_auth(token)
    )
    assert listed.status_code == 200
    endpoints = listed.json()
    assert len(endpoints) == len(EXPECTED_ENDPOINTS)
    assert {
        (endpoint["path"], endpoint["method"]) for endpoint in endpoints
    } == EXPECTED_ENDPOINTS

    # Path-level parameters are merged into each operation row.
    user_get = next(
        endpoint
        for endpoint in endpoints
        if endpoint["path"] == "/users/{user_id}"
        and endpoint["method"] == "GET"
    )
    assert user_get["parameters"] == [
        {"name": "user_id", "in": "path", "required": True}
    ]

    users_get = next(
        endpoint
        for endpoint in endpoints
        if endpoint["path"] == "/users" and endpoint["method"] == "GET"
    )
    assert users_get["parameters"] == [{"name": "limit", "in": "query"}]

    users_post = next(
        endpoint
        for endpoint in endpoints
        if endpoint["path"] == "/users" and endpoint["method"] == "POST"
    )
    assert users_post["parameters"] is None


def test_reupload_replaces_endpoints_without_duplicates(client) -> None:
    _, token = _register(client, _email("owner"))
    target_id = _create_project_with_target(client, token)

    assert _upload_spec(client, token, target_id).json()["endpoints_count"] == 5
    assert _upload_spec(client, token, target_id).json()["endpoints_count"] == 5

    listed = client.get(
        f"/targets/{target_id}/endpoints", headers=_auth(token)
    ).json()
    assert len(listed) == 5


def test_endpoints_scoped_to_owner_and_require_auth(client) -> None:
    _, owner_token = _register(client, _email("owner"))
    _, other_token = _register(client, _email("other"))
    target_id = _create_project_with_target(client, owner_token)
    _upload_spec(client, owner_token, target_id)

    assert (
        client.get(
            f"/targets/{target_id}/endpoints", headers=_auth(other_token)
        ).status_code
        == 404
    )
    assert (
        client.get(f"/targets/{target_id}/endpoints").status_code == 401
    )
