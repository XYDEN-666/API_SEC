"""Project CRUD endpoint tests: ownership scoping."""

import uuid

PASSWORD = "CorrectHorse42!"


def _email(prefix: str) -> str:
    return f"test-{prefix}-{uuid.uuid4().hex}@example.com"


def _auth_headers(token: str) -> dict[str, str]:
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


def test_project_crud_scoped_to_owner(client) -> None:
    user_id, token = _register(client, _email("owner"))
    headers = _auth_headers(token)

    create = client.post(
        "/projects", json={"name": "My API"}, headers=headers
    )
    assert create.status_code == 201
    project = create.json()
    assert project["name"] == "My API"
    assert project["owner_id"] == user_id
    project_id = project["id"]

    listed = client.get("/projects", headers=headers)
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [project_id]

    retrieved = client.get(f"/projects/{project_id}", headers=headers)
    assert retrieved.status_code == 200
    assert retrieved.json()["name"] == "My API"

    updated = client.put(
        f"/projects/{project_id}",
        json={"name": "Renamed API"},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Renamed API"

    deleted = client.delete(f"/projects/{project_id}", headers=headers)
    assert deleted.status_code == 204

    assert client.get("/projects", headers=headers).json() == []


def test_cannot_access_another_users_project(client) -> None:
    owner_id, owner_token = _register(client, _email("owner"))
    _, other_token = _register(client, _email("other"))
    owner_headers = _auth_headers(owner_token)
    other_headers = _auth_headers(other_token)

    created = client.post(
        "/projects", json={"name": "Private"}, headers=owner_headers
    )
    assert created.status_code == 201
    project_id = created.json()["id"]

    assert (
        client.get(f"/projects/{project_id}", headers=other_headers).status_code
        == 404
    )
    assert (
        client.put(
            f"/projects/{project_id}",
            json={"name": "Hijacked"},
            headers=other_headers,
        ).status_code
        == 404
    )
    assert (
        client.delete(
            f"/projects/{project_id}", headers=other_headers
        ).status_code
        == 404
    )

    # Owner's project is untouched.
    listed = client.get("/projects", headers=owner_headers)
    assert [item["id"] for item in listed.json()] == [project_id]
    assert listed.json()[0]["name"] == "Private"
    assert owner_id == created.json()["owner_id"]


def test_projects_require_authentication(client) -> None:
    assert client.get("/projects").status_code == 401
    assert client.post("/projects", json={"name": "x"}).status_code == 401
    assert client.get("/projects/1").status_code == 401
    assert client.put("/projects/1", json={"name": "x"}).status_code == 401
    assert client.delete("/projects/1").status_code == 401
