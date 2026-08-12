"""Target CRUD endpoint tests: project ownership scoping."""

import uuid

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


def _create_project(client, token: str, name: str = "API Project") -> int:
    response = client.post(
        "/projects", json={"name": name}, headers=_auth(token)
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_target_crud_scoped_to_parent_project(client) -> None:
    _, token = _register(client, _email("owner"))
    headers = _auth(token)
    project_id = _create_project(client, token)

    create = client.post(
        f"/projects/{project_id}/targets",
        json={"name": "API", "base_url": "https://api.example.com"},
        headers=headers,
    )
    assert create.status_code == 201
    target = create.json()
    assert target["project_id"] == project_id
    assert target["name"] == "API"
    assert target["base_url"] == "https://api.example.com"
    target_id = target["id"]

    listed = client.get(f"/projects/{project_id}/targets", headers=headers)
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [target_id]

    retrieved = client.get(f"/targets/{target_id}", headers=headers)
    assert retrieved.status_code == 200
    assert retrieved.json()["base_url"] == "https://api.example.com"

    updated = client.put(
        f"/targets/{target_id}",
        json={"name": "API v2", "base_url": "https://api2.example.com"},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "API v2"

    assert (
        client.delete(f"/targets/{target_id}", headers=headers).status_code
        == 204
    )
    assert client.get(f"/projects/{project_id}/targets", headers=headers).json() == []


def test_targets_inherit_project_ownership_check(client) -> None:
    _, owner_token = _register(client, _email("owner"))
    _, other_token = _register(client, _email("other"))
    project_id = _create_project(client, owner_token)

    created = client.post(
        f"/projects/{project_id}/targets",
        json={"name": "API", "base_url": "https://api.example.com"},
        headers=_auth(owner_token),
    )
    assert created.status_code == 201
    target_id = created.json()["id"]

    other_headers = _auth(other_token)
    assert (
        client.post(
            f"/projects/{project_id}/targets",
            json={"name": "Hijack", "base_url": "https://x.example.com"},
            headers=other_headers,
        ).status_code
        == 404
    )
    assert (
        client.get(
            f"/projects/{project_id}/targets", headers=other_headers
        ).status_code
        == 404
    )
    assert client.get(f"/targets/{target_id}", headers=other_headers).status_code == 404
    assert (
        client.put(
            f"/targets/{target_id}",
            json={"name": "Hijack", "base_url": "https://x.example.com"},
            headers=other_headers,
        ).status_code
        == 404
    )
    assert (
        client.delete(f"/targets/{target_id}", headers=other_headers).status_code
        == 404
    )

    # Owner still sees the untouched target.
    listed = client.get(f"/projects/{project_id}/targets", headers=_auth(owner_token))
    assert listed.json()[0]["name"] == "API"


def test_targets_require_authentication(client) -> None:
    assert (
        client.post(
            "/projects/1/targets",
            json={"name": "x", "base_url": "https://x"},
        ).status_code
        == 401
    )
    assert client.get("/projects/1/targets").status_code == 401
    assert client.get("/targets/1").status_code == 401
    assert (
        client.put(
            "/targets/1", json={"name": "x", "base_url": "https://x"}
        ).status_code
        == 401
    )
    assert client.delete("/targets/1").status_code == 401
