"""Authorization record CRUD endpoint tests: project ownership scoping."""

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


def test_authorization_record_crud(client) -> None:
    _, token = _register(client, _email("owner"))
    headers = _auth(token)
    project_id = _create_project(client, token)

    create = client.post(
        f"/projects/{project_id}/authorization-records",
        json={
            "description": "Authorized to scan production",
            "scope_notes": "Only /api/v1 endpoints",
        },
        headers=headers,
    )
    assert create.status_code == 201
    record = create.json()
    assert record["project_id"] == project_id
    assert record["description"] == "Authorized to scan production"
    assert record["scope_notes"] == "Only /api/v1 endpoints"
    record_id = record["id"]

    listed = client.get(
        f"/projects/{project_id}/authorization-records", headers=headers
    )
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [record_id]

    retrieved = client.get(
        f"/authorization-records/{record_id}", headers=headers
    )
    assert retrieved.status_code == 200
    assert retrieved.json()["description"] == "Authorized to scan production"

    updated = client.put(
        f"/authorization-records/{record_id}",
        json={
            "description": "Scope expanded",
            "scope_notes": "All endpoints",
        },
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["description"] == "Scope expanded"
    assert updated.json()["scope_notes"] == "All endpoints"

    assert (
        client.delete(
            f"/authorization-records/{record_id}", headers=headers
        ).status_code
        == 204
    )
    assert (
        client.get(
            f"/projects/{project_id}/authorization-records", headers=headers
        ).json()
        == []
    )


def test_authorization_records_inherit_project_ownership(client) -> None:
    _, owner_token = _register(client, _email("owner"))
    _, other_token = _register(client, _email("other"))
    project_id = _create_project(client, owner_token)

    created = client.post(
        f"/projects/{project_id}/authorization-records",
        json={"description": "Owner only"},
        headers=_auth(owner_token),
    )
    assert created.status_code == 201
    record_id = created.json()["id"]

    other_headers = _auth(other_token)
    assert (
        client.post(
            f"/projects/{project_id}/authorization-records",
            json={"description": "Hijack"},
            headers=other_headers,
        ).status_code
        == 404
    )
    assert (
        client.get(
            f"/projects/{project_id}/authorization-records",
            headers=other_headers,
        ).status_code
        == 404
    )
    assert (
        client.get(
            f"/authorization-records/{record_id}", headers=other_headers
        ).status_code
        == 404
    )
    assert (
        client.put(
            f"/authorization-records/{record_id}",
            json={"description": "Hijack"},
            headers=other_headers,
        ).status_code
        == 404
    )
    assert (
        client.delete(
            f"/authorization-records/{record_id}", headers=other_headers
        ).status_code
        == 404
    )

    listed = client.get(
        f"/projects/{project_id}/authorization-records",
        headers=_auth(owner_token),
    )
    assert listed.json()[0]["description"] == "Owner only"


def test_authorization_records_require_authentication(client) -> None:
    assert (
        client.post(
            "/projects/1/authorization-records",
            json={"description": "x"},
        ).status_code
        == 401
    )
    assert client.get("/projects/1/authorization-records").status_code == 401
    assert client.get("/authorization-records/1").status_code == 401
    assert (
        client.put(
            "/authorization-records/1", json={"description": "x"}
        ).status_code
        == 401
    )
    assert client.delete("/authorization-records/1").status_code == 401
